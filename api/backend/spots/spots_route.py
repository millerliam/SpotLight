from __future__ import annotations
from flask import Blueprint, request, jsonify, current_app
from backend.db_connection import db  
from typing import Any, List


spots = Blueprint("spots", __name__)

VALID_STATUSES = {"free", "inuse", "planned", "w.issue"}

# ------------------------- helpers -------------------------

def _valid_status(s: str | None) -> bool:
    return bool(s) and s in VALID_STATUSES

def _numbers(*vals):
    try:
        return [float(v) for v in vals]
    except Exception:
        return None

def _close(cursor, conn):
    try:
        if cursor: cursor.close()
    finally:
        try:
            if conn: conn.close()
        except Exception:
            pass

# ------------------------- routes --------------------------

@spots.route("/", methods=["GET"])
def list_spots():
    """
    GET /spots/
    Optional query params:
      status=free,inuse,planned,w.issue
      bbox=minLon,minLat,maxLon,maxLat
      q=<address contains> (also supports key_word=)
      sort=spotID|price|views|status   order=asc|desc
      limit (1..1000), offset (>=0)
    """
    conn = cursor = None
    try:
        where: List[str] = ["latitude IS NOT NULL", "longitude IS NOT NULL"]
        params: List[Any] = []

        # status filter
        s = (request.args.get("status") or "").strip()
        if s:
            vals = [x.strip() for x in s.split(",") if x.strip()]
            if vals:
                where.append("status IN (" + ",".join(["%s"] * len(vals)) + ")")
                params.extend(vals)

        # bbox filter
        bbox = (request.args.get("bbox") or "").strip()
        if bbox:
            parts = bbox.split(",")
            if len(parts) != 4:
                return jsonify({"error": "bbox must be 'minLon,minLat,maxLon,maxLat'"}), 400
            nums = _numbers(*parts)
            if not nums:
                return jsonify({"error": "bbox must be numeric"}), 400
            min_lon, min_lat, max_lon, max_lat = nums
            where.append("longitude BETWEEN %s AND %s")
            where.append("latitude BETWEEN %s AND %s")
            params += [min_lon, max_lon, min_lat, max_lat]

        # q / key_word
        q = (request.args.get("q") or request.args.get("key_word") or "").strip()
        if q:
            where.append("address LIKE %s")
            params.append(f"%{q}%")

        # sort / page
        sort_map = {"spotID": "spotID", "price": "price", "views": "estViewPerMonth", "status": "status"}
        sort = sort_map.get(request.args.get("sort", "spotID"), "spotID")
        order = "DESC" if request.args.get("order", "asc").lower() == "desc" else "ASC"
        try:
            limit = max(1, min(1000, int(request.args.get("limit", "300"))))
            offset = max(0, int(request.args.get("offset", "0")))
        except ValueError:
            return jsonify({"error": "limit/offset must be integers"}), 400

        sql = (
            "SELECT spotID, price, contactTel, estViewPerMonth, monthlyRentCost, "
            "endTimeOfCurrentOrder, status, address, longitude, latitude, imageURL "
            f"FROM Spot WHERE {' AND '.join(where)} ORDER BY {sort} {order} LIMIT %s OFFSET %s"
        )
        params += [limit, offset]

        conn = db.connect()
        cursor = conn.cursor()  # DictCursor set in db_connection
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return jsonify(rows), 200

    except Exception as e:
        current_app.logger.error(f"list_spots error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        _close(cursor, conn)


@spots.route("/", methods=["POST"])
def create_spot():
    """POST /spots/  (auto assigns spotID)"""
    conn = cursor = None
    try:
        payload = request.get_json(silent=True) or {}
        required = [
            "price","contactTel","estViewPerMonth","monthlyRentCost",
            "endTimeOfCurrentOrder","status","address","longitude","latitude"
        ]
        missing = [f for f in required if f not in payload]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
        if not _valid_status(payload.get("status")):
            return jsonify({"error": "Invalid status"}), 400

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Spot (price,contactTel,estViewPerMonth,monthlyRentCost,endTimeOfCurrentOrder,"
            "status,address,longitude,latitude,imageURL) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                payload["price"], payload["contactTel"], payload["estViewPerMonth"], payload["monthlyRentCost"],
                payload["endTimeOfCurrentOrder"], payload["status"], payload["address"],
                payload["longitude"], payload["latitude"], payload.get("imageURL")
            ),
        )
        conn.commit()
        return jsonify({"message": "created", "spotID": cursor.lastrowid}), 201
    except Exception as e:
        current_app.logger.error(f"create_spot error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        _close(cursor, conn)


@spots.route("/<int:spot_id>", methods=["GET"])
def get_spot(spot_id: int):
    conn = cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT spotID, price, contactTel, estViewPerMonth, monthlyRentCost, endTimeOfCurrentOrder, "
            "status, address, longitude, latitude, imageURL FROM Spot WHERE spotID=%s",
            (spot_id,),
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "not found"}), 404
        return jsonify(row), 200
    except Exception as e:
        current_app.logger.error(f"get_spot error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        _close(cursor, conn)


@spots.route("/<int:spot_id>", methods=["PUT"])
def update_spot(spot_id: int):
    """
    Partial update. Editable fields:
      price, contactTel, estViewPerMonth, monthlyRentCost, endTimeOfCurrentOrder,
      status, address, longitude, latitude, imageURL
    """
    conn = cursor = None
    try:
        payload = request.get_json(silent=True) or {}
        if not payload:
            return jsonify({"error": "empty body"}), 400

        allowed = {
            "price","contactTel","estViewPerMonth","monthlyRentCost","endTimeOfCurrentOrder",
            "status","address","longitude","latitude","imageURL"
        }
        keys = [k for k in payload if k in allowed]
        if not keys:
            return jsonify({"error": "no editable fields provided"}), 400
        if "status" in keys and not _valid_status(payload.get("status")):
            return jsonify({"error": "Invalid status"}), 400

        sets = ", ".join(f"{k}=%s" for k in keys)
        values = [payload[k] for k in keys] + [spot_id]

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE Spot SET {sets} WHERE spotID=%s", tuple(values))
        conn.commit()
        return jsonify({"message": "updated", "spotID": spot_id}), 200

    except Exception as e:
        current_app.logger.error(f"update_spot error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        _close(cursor, conn)


@spots.route("/<int:spot_id>", methods=["DELETE"])
def delete_spot(spot_id: int):
    conn = cursor = None
    try:
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Spot WHERE spotID=%s", (spot_id,))
        conn.commit()
        return jsonify({"message": "deleted", "spotID": spot_id}), 200
    except Exception as e:
        current_app.logger.error(f"delete_spot error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        _close(cursor, conn)



@spots.route("/near", methods=["GET"])
def find_spots_near():
    """
    GET /spots/near?lat=29.6516&lon=-82.3248&radius_km=5&status=free
    (also accepts lng=)
    """
    conn = cursor = None
    try:
        lat_s = request.args.get("lat")
        lon_s = request.args.get("lon") or request.args.get("lng")
        radius_s = request.args.get("radius_km") or "5"
        status = request.args.get("status")

        if not lat_s or not lon_s:
            return jsonify({"error": "Missing required query params: lat, lon"}), 400
        nums = _numbers(lat_s, lon_s, radius_s)
        if not nums:
            return jsonify({"error": "lat, lon, radius_km must be numeric"}), 400
        lat, lon, radius_km = nums
        if status and not _valid_status(status):
            return jsonify({"error": "Invalid status"}), 400

        params: List[Any] = [lat, lon, lat]
        sql = (
            "SELECT spotID, price, contactTel, estViewPerMonth, monthlyRentCost, endTimeOfCurrentOrder, "
            "status, address, longitude, latitude, "
            "(6371 * acos( cos(radians(%s)) * cos(radians(latitude)) * "
            "cos(radians(longitude) - radians(%s)) + sin(radians(%s)) * sin(radians(latitude)) )) AS distance_km "
            "FROM Spot WHERE latitude IS NOT NULL AND longitude IS NOT NULL "
        )
        if status:
            sql += "AND status=%s "
            params.append(status)
        sql += "HAVING distance_km <= %s ORDER BY distance_km ASC LIMIT 100"
        params.append(radius_km)

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return jsonify(rows), 200

    except Exception as e:
        current_app.logger.error(f"find_spots_near error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        _close(cursor, conn)


@spots.route("/search", methods=["GET"])
def search_spots():
    """
    GET /spots/search?q=Main&top_n=20
    Also supports key_word=. Falls back to LIKE if FULLTEXT is unavailable.
    """
    conn = cursor = None
    try:
        q = (request.args.get("q") or request.args.get("key_word") or "").strip()
        top_n_raw = (request.args.get("top_n") or "20").strip()
        if not q:
            return jsonify([]), 200
        try:
            top_n = max(1, min(200, int(top_n_raw)))
        except Exception:
            return jsonify({"error": "top_n must be an integer"}), 400

        conn = db.connect()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT spotID, price, contactTel, estViewPerMonth, monthlyRentCost, endTimeOfCurrentOrder, "
                "status, address, longitude, latitude "
                "FROM Spot WHERE MATCH(address) AGAINST (%s IN NATURAL LANGUAGE MODE) LIMIT %s",
                (q, top_n),
            )
        except Exception:
            cursor.execute(
                "SELECT spotID, price, contactTel, estViewPerMonth, monthlyRentCost, endTimeOfCurrentOrder, "
                "status, address, longitude, latitude "
                "FROM Spot WHERE address LIKE %s LIMIT %s",
                "(f\"%{q}%\", top_n)",
                 )
        rows = cursor.fetchall()
        return jsonify(rows), 200

    except Exception as e:
        current_app.logger.error(f"search_spots error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        _close(cursor, conn)
