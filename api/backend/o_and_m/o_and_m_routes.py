import mysql.connector as mysql
from flask import Blueprint, request, jsonify, current_app
from mysql.connector import Error
from datetime import datetime, timedelta


o_and_m = Blueprint("o_and_m", __name__)


def _get_database_connection():
    """Get a fresh database connection using Flask config"""
    cfg = current_app.config
    return mysql.connect(
        host=cfg.get("MYSQL_DATABASE_HOST", "127.0.0.1"),
        port=int(cfg.get("MYSQL_DATABASE_PORT", 3306)),
        user=cfg.get("MYSQL_DATABASE_USER", "root"),
        password=cfg.get("MYSQL_DATABASE_PASSWORD", "changeme"),
        database=cfg.get("MYSQL_DATABASE_DB", "SpotLight"),
    )


def _execute_query(query, params=None, fetch_one=False, fetch_all=False, dictionary=False):
    """Execute a database query with consistent error handling and connection management"""
    connection = None
    cursor = None
    try:
        connection = _get_database_connection()
        cursor = connection.cursor(dictionary=dictionary)
        cursor.execute(query, params or ())
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.rowcount
            connection.commit()
        
        return result, None
    except Error as e:
        current_app.logger.error(f"Database error: {e}")
        return None, str(e)
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return None, str(e)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def _parse_period_days(period_param: str, default_days: int = 90) -> int:
    """Parse period parameter into number of days"""
    if not period_param:
        return default_days
    try:
        # supports formats like "90d"
        if period_param.endswith("d"):
            return int(period_param[:-1])
        return int(period_param)
    except Exception:
        return default_days


@o_and_m.route("/search", methods=["GET"])
def full_db_search():
    """Search across all entities (spots, customers, orders)"""
    try:
        q = request.args.get("query", "").strip()
        if not q:
            return jsonify({"spots": [], "customers": [], "orders": []}), 200

        connection = _get_database_connection()
        cursor = connection.cursor()
        
        # Search spots: use FULLTEXT on address when possible, also fallback to LIKE
        spots = []
        try:
            spots_query = (
                "SELECT spotID, address, status, price, estViewPerMonth, monthlyRentCost "
                "FROM Spot WHERE MATCH(address) AGAINST (%s IN NATURAL LANGUAGE MODE) "
                "OR address LIKE %s LIMIT 20"
            )
            cursor.execute(spots_query, (q, f"%{q}%"))
            spots = cursor.fetchall()
        except Error:
            # In case MATCH is unsupported in current mode
            fallback_query = (
                "SELECT spotID, address, status, price, estViewPerMonth, monthlyRentCost "
                "FROM Spot WHERE address LIKE %s LIMIT 20"
            )
            cursor.execute(fallback_query, (f"%{q}%",))
            spots = cursor.fetchall()

        # Search customers: search by name/email/company
        customers_query = (
            "SELECT cID, fName, lName, email, companyName, VIP "
            "FROM Customers "
            "WHERE fName LIKE %s OR lName LIKE %s OR email LIKE %s OR companyName LIKE %s "
            "LIMIT 20"
        )
        cursor.execute(customers_query, (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"))
        customers = cursor.fetchall()

        # Search orders: if numeric, try exact match on orderID or cID; else search by date string
        orders = []
        if q.isdigit():
            orders_query = (
                "SELECT orderID, date, total, cID "
                "FROM Orders WHERE orderID = %s OR cID = %s LIMIT 20"
            )
            cursor.execute(orders_query, (int(q), int(q)))
            orders = cursor.fetchall()
        else:
            orders_query = (
                "SELECT orderID, date, total, cID "
                "FROM Orders WHERE DATE_FORMAT(date, '%%Y-%%m-%%d') LIKE %s LIMIT 20"
            )
            cursor.execute(orders_query, (f"%{q}%",))
            orders = cursor.fetchall()

        cursor.close()
        connection.close()
        return jsonify({"spots": spots, "customers": customers, "orders": orders}), 200
        
    except Error as e:
        current_app.logger.error(f"full_db_search error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"full_db_search unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@o_and_m.route("/insert", methods=["POST"])
def insert_data():
    """Insert new data for spots, customers, or orders"""
    try:
        payload = request.get_json(silent=True) or {}
        entity = (payload.get("entity") or "").strip().lower()
        if not entity:
            return jsonify({"error": "Missing entity"}), 400

        if entity == "spot":
            required = ["price", "contactTel", "address"]
            missing_fields = [f for f in required if f not in payload]
            if missing_fields:
                return jsonify({"error": f"Missing field: {', '.join(missing_fields)}"}), 400
            
            status = payload.get("status", "free")
            if status not in ("free", "inuse", "w.issue", "planned"):
                return jsonify({"error": "Invalid status"}), 400
            
            query = (
                "INSERT INTO Spot (price, contactTel, imageURL, estViewPerMonth, monthlyRentCost, "
                "endTimeOfCurrentOrder, status, address, latitude, longitude) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
            data = (
                payload["price"],
                payload["contactTel"],
                payload.get("imageURL"),
                payload.get("estViewPerMonth"),
                payload.get("monthlyRentCost"),
                payload.get("endTimeOfCurrentOrder"),
                status,
                payload["address"],
                payload.get("latitude"),
                payload.get("longitude"),
            )
            
            connection = _get_database_connection()
            cursor = connection.cursor()
            cursor.execute(query, data)
            connection.commit()
            new_id = cursor.lastrowid
            cursor.close()
            connection.close()
            return jsonify({"message": "created", "spotID": new_id}), 201

        elif entity == "customer":
            required = ["fName", "lName", "email"]
            missing_fields = [f for f in required if f not in payload]
            if missing_fields:
                return jsonify({"error": f"Missing field: {', '.join(missing_fields)}"}), 400
            
            query = (
                "INSERT INTO Customers (fName, lName, email, position, companyName, totalOrderTimes, VIP, avatarURL, balance, TEL) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
            data = (
                payload["fName"],
                payload["lName"],
                payload["email"],
                payload.get("position"),
                payload.get("companyName"),
                payload.get("totalOrderTimes", 0),
                bool(payload.get("VIP", False)),
                payload.get("avatarURL"),
                payload.get("balance", 0),
                payload.get("TEL"),
            )
            
            connection = _get_database_connection()
            cursor = connection.cursor()
            cursor.execute(query, data)
            connection.commit()
            new_id = cursor.lastrowid
            cursor.close()
            connection.close()
            return jsonify({"message": "created", "cID": new_id}), 201

        elif entity == "order":
            required = ["date", "total", "cID"]
            missing_fields = [f for f in required if f not in payload]
            if missing_fields:
                return jsonify({"error": f"Missing field: {', '.join(missing_fields)}"}), 400
            
            query = "INSERT INTO Orders (date, total, cID) VALUES (%s, %s, %s)"
            data = (payload["date"], payload["total"], payload["cID"])
            
            connection = _get_database_connection()
            cursor = connection.cursor()
            cursor.execute(query, data)
            connection.commit()
            new_id = cursor.lastrowid
            cursor.close()
            connection.close()
            return jsonify({"message": "created", "orderID": new_id}), 201

        else:
            return jsonify({"error": "Unsupported entity. Use one of: spot, customer, order"}), 400
            
    except Error as e:
        current_app.logger.error(f"insert_data error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"insert_data unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@o_and_m.route("/spots/metrics", methods=["GET"])
def get_spots_metrics():
    """Get metrics for all spots"""
    try:
        connection = _get_database_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM Spot")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM Spot WHERE status = 'inuse'")
        in_use = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM Spot WHERE status = 'free'")
        free = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) AS cnt FROM Spot WHERE status = 'w.issue'")
        with_issue = cursor.fetchone()["cnt"]

        cursor.close()
        connection.close()
        
        return jsonify({
            "total": total,
            "in_use": in_use,
            "free": free,
            "with_issue": with_issue,
        }), 200
        
    except Error as e:
        current_app.logger.error(f"get_spots_metrics error: {e}")
        return jsonify({"error": str(e)}), 500


@o_and_m.route("/customers/metrics", methods=["GET"])
def get_customers_metrics():
    """Get metrics for all customers"""
    try:
        connection = _get_database_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM Customers")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS vip FROM Customers WHERE VIP = 1")
        vip = cursor.fetchone()["vip"]

        cursor.execute(
            "SELECT COUNT(*) AS never_ordered FROM Customers c "
            "LEFT JOIN Orders o ON o.cID = c.cID WHERE o.orderID IS NULL"
        )
        never_ordered = cursor.fetchone()["never_ordered"]

        # Average days since last order across customers having at least 1 order
        cursor.execute(
            "SELECT AVG(days_since) AS avg_days FROM ("
            "  SELECT DATEDIFF(CURDATE(), MAX(o.date)) AS days_since"
            "  FROM Orders o GROUP BY o.cID"
            ") t"
        )
        row = cursor.fetchone()
        avg_order_time = row["avg_days"] if row and row["avg_days"] is not None else 0

        cursor.close()
        connection.close()
        
        return jsonify({
            "total": total,
            "vip": vip,
            "never_ordered": never_ordered,
            "avg_order_time": avg_order_time,
        }), 200
        
    except Error as e:
        current_app.logger.error(f"get_customers_metrics error: {e}")
        return jsonify({"error": str(e)}), 500


@o_and_m.route("/orders/metrics", methods=["GET"])
def get_orders_metrics():
    """Get metrics for all orders with optional time period"""
    try:
        period_param = request.args.get("period", "90d")
        days = _parse_period_days(period_param, 90)

        connection = _get_database_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM Orders")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT AVG(total) AS avg_price FROM Orders")
        avg_price = cursor.fetchone()["avg_price"]

        cursor.execute(
            "SELECT COUNT(*) AS last_period FROM Orders WHERE date >= (CURDATE() - INTERVAL %s DAY)",
            (days,),
        )
        last_period = cursor.fetchone()["last_period"]

        cursor.close()
        connection.close()
        
        return jsonify({
            "total": total,
            "avg_price": avg_price,
            "last_period": last_period,
        }), 200
        
    except Error as e:
        current_app.logger.error(f"get_orders_metrics error: {e}")
        return jsonify({"error": str(e)}), 500


@o_and_m.route("/spots/summary", methods=["GET"])
def spots_summary():
    """Get summary of recent spots"""
    try:
        limit = int(request.args.get("limit", 10))
        
        query = (
            "SELECT spotID, address, status, price, estViewPerMonth, monthlyRentCost "
            "FROM Spot ORDER BY spotID DESC LIMIT %s"
        )
        
        result, error = _execute_query(query, (limit,), fetch_all=True)
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify(result), 200
        
    except ValueError:
        return jsonify({"error": "Invalid limit parameter"}), 400
    except Exception as e:
        current_app.logger.error(f"spots_summary error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@o_and_m.route("/customers/summary", methods=["GET"])
def customers_summary():
    """Get summary of recent customers"""
    try:
        limit = int(request.args.get("limit", 10))
        
        query = (
            "SELECT cID, fName, lName, email, companyName, VIP, totalOrderTimes "
            "FROM Customers ORDER BY cID DESC LIMIT %s"
        )
        
        result, error = _execute_query(query, (limit,), fetch_all=True)
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify(result), 200
        
    except ValueError:
        return jsonify({"error": "Invalid limit parameter"}), 400
    except Exception as e:
        current_app.logger.error(f"customers_summary error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@o_and_m.route("/orders/summary", methods=["GET"])
def orders_summary():
    """Get summary of recent orders within a time period"""
    try:
        period_param = request.args.get("period", "90d")
        days = _parse_period_days(period_param, 90)
        limit = int(request.args.get("limit", 10))

        query = (
            "SELECT orderID, date, total, cID "
            "FROM Orders WHERE date >= (CURDATE() - INTERVAL %s DAY) "
            "ORDER BY date DESC, orderID DESC LIMIT %s"
        )
        
        result, error = _execute_query(query, (days, limit), fetch_all=True)
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify(result), 200
        
    except ValueError:
        return jsonify({"error": "Invalid limit parameter"}), 400
    except Exception as e:
        current_app.logger.error(f"orders_summary error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@o_and_m.route("/reports/<int:r_id>", methods=["DELETE"])
def delete_report(r_id: int):
    """Delete a report by ID"""
    query = "DELETE FROM Report WHERE rID = %s"
    
    rows_affected, error = _execute_query(query, (r_id,))
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"message": "deleted", "rID": r_id}), 200


@o_and_m.route("/reports/<int:r_id>/status", methods=["PUT"])
def update_report_status(r_id: int):
    """Update report status"""
    try:
        payload = request.get_json(silent=True) or {}
        status = payload.get("status")
        
        # According to schema, valid values: 'unexamined', 'examined'
        if status not in ("unexamined", "examined"):
            return jsonify({"error": "Invalid status. Allowed: unexamined, examined"}), 400
        
        query = "UPDATE Report SET status = %s WHERE rID = %s"
        
        rows_affected, error = _execute_query(query, (status, r_id))
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify({"message": "updated", "rID": r_id, "status": status}), 200
        
    except Exception as e:
        current_app.logger.error(f"update_report_status error: {e}")
        return jsonify({"error": "Internal server error"}), 500