#owner_route.py
from flask import Blueprint, request, jsonify, current_app
import mysql.connector as mysql

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")
owner_bp.strict_slashes = False

def _get_conn():
    cfg = current_app.config
    return mysql.connect(
        host=cfg.get("MYSQL_DATABASE_HOST", "127.0.0.1"),
        port=int(cfg.get("MYSQL_DATABASE_PORT", 3306)),
        user=cfg.get("MYSQL_DATABASE_USER", "root"),
        password=cfg.get("MYSQL_DATABASE_PASSWORD", "changeme"),
        database=cfg.get("MYSQL_DATABASE_DB", "SpotLight"),
    )

def _table_exists(cur, name):
    cur.execute("SHOW TABLES LIKE %s", (name,))
    return cur.fetchone() is not None

def _column_exists(cur, table, column):
    cur.execute(f"SHOW COLUMNS FROM `{table}` LIKE %s", (column,))
    return cur.fetchone() is not None

@owner_bp.get("/metrics")
def metrics():
    """High-level counts for the ads company owner."""
    try:
        conn = _get_conn(); cur = conn.cursor(dictionary=True)
        out = {}
        for t in ("Spot", "Customers", "Orders", "Reviews", "Employee", "SalesMan"):
            cur.execute("SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s", (t,))
            if cur.fetchone()["n"]:
                cur.execute(f"SELECT COUNT(*) AS cnt FROM `{t}`")
                out[f"{t.lower()}_count"] = cur.fetchone()["cnt"]

        # Spot status breakdown (only if column exists)
        if _table_exists(cur, "Spot") and _column_exists(cur, "Spot", "status"):
            cur.execute("SELECT status, COUNT(*) AS cnt FROM Spot GROUP BY status ORDER BY cnt DESC")
            out["spot_status"] = cur.fetchall()

        cur.close(); conn.close()
        return jsonify(out), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@owner_bp.post("/spots/bulk-price")
def bulk_price():
    """
    Bulk price update by percentage.
    Body:
      { "percent": 10, "status": "free" }  -> +10% for all Spot with status='free'
    """
    body = request.get_json(silent=True) or {}
    try:
        pct = float(body.get("percent", 0))
    except Exception:
        return jsonify({"error": "percent must be a number"}), 400
    status = body.get("status")

    try:
        conn = _get_conn(); cur = conn.cursor(dictionary=True)
        if not _table_exists(cur, "Spot"):
            return jsonify({"error": "table Spot not found"}), 400
        if not _column_exists(cur, "Spot", "price"):
            return jsonify({"error": "column 'price' not found on Spot"}), 400

        if status:
            cur.execute("UPDATE Spot SET price = ROUND(price * (1 + %s/100), 2) WHERE status=%s", (pct, status))
        else:
            cur.execute("UPDATE Spot SET price = ROUND(price * (1 + %s/100), 2)", (pct,))
        conn.commit()

        # return summary
        cur.execute("SELECT COUNT(*) AS n, MIN(price) AS min_price, MAX(price) AS max_price, AVG(price) AS avg_price FROM Spot")
        summary = cur.fetchone()
        cur.close(); conn.close()
        return jsonify({"updated_percent": pct, "status_filter": status, "summary": summary}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@owner_bp.get("/orders/recent")
def recent_orders():
    """Recent orders (top 50)."""
    try:
        conn = _get_conn(); cur = conn.cursor(dictionary=True)
        if not _table_exists(cur, "Orders"):
            return jsonify({"data": [], "note": "table Orders not found"}), 200
        # Avoid assuming column names: select * with limit
        cur.execute("SELECT * FROM Orders ORDER BY 1 DESC LIMIT 50")
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify(rows), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@owner_bp.delete("/reviews/<int:rid>")
def delete_review(rid: int):
    """Moderate a review (owner deletes)."""
    try:
        conn = _get_conn(); cur = conn.cursor()
        if not _table_exists(cur, "Reviews"):
            return jsonify({"error": "table Reviews not found"}), 400
        cur.execute("DELETE FROM Reviews WHERE rID=%s", (rid,))
        conn.commit()
        cur.close(); conn.close()
        return jsonify({"deleted": rid}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@owner_bp.put("/spots/<int:spot_id>/status")
def update_spot_status(spot_id: int):
    """
    Owner updates a spot's status (e.g., free, inuse, planned, w.issue).
    Body: { "status": "free" }
    """
    body = request.get_json(silent=True) or {}
    new_status = (body.get("status") or "").strip()
    if not new_status:
        return {"error": "Missing 'status' in JSON body"}, 400
    try:
        conn = _get_conn(); cur = conn.cursor(dictionary=True)
        cur.execute("UPDATE Spot SET status=%s WHERE spotID=%s", (new_status, spot_id))
        conn.commit()
        cur.execute("SELECT spotID, address, status, latitude, longitude FROM Spot WHERE spotID=%s", (spot_id,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if not row:
            return {"error": f"spotID {spot_id} not found"}, 404
        return row, 200
    except Exception as e:
        return {"error": str(e)}, 500


