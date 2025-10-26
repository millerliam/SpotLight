import mysql.connector as mysql
from flask import Blueprint, request, jsonify, current_app
from mysql.connector import Error
from datetime import datetime

# Blueprint setup
customer = Blueprint("customer", __name__, url_prefix="/customer")
customer.strict_slashes = False


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


@customer.route("/<int:c_id>", methods=["GET"])
def get_customer(c_id: int):
    """Get a specific customer by ID"""
    query = (
        "SELECT cID, fName, lName, email, position, companyName, "
        "totalOrderTimes, VIP, avatarURL, balance, TEL "
        "FROM Customers WHERE cID = %s"
    )
    
    result, error = _execute_query(query, (c_id,), fetch_one=True)
    
    if error:
        return jsonify({"error": error}), 500
    
    if not result:
        return jsonify({"error": "Customer not found"}), 404
    
    return jsonify(result), 200


@customer.route("/<int:c_id>", methods=["POST"])
def update_customer(c_id: int):
    """Update a specific customer by ID"""
    try:
        payload = request.get_json(silent=True) or {}
        
        # Validate required fields
        required_fields = [
            "fName", "lName", "email", "position", "companyName",
            "totalOrderTimes", "VIP", "avatarURL", "balance", "TEL"
        ]
        
        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400
        
        # Prepare update query and data
        query = (
            "UPDATE Customers SET fName=%s, lName=%s, email=%s, position=%s, "
            "companyName=%s, totalOrderTimes=%s, VIP=%s, avatarURL=%s, "
            "balance=%s, TEL=%s WHERE cID=%s"
        )
        
        data = (
            payload["fName"],
            payload["lName"],
            payload["email"],
            payload["position"],
            payload["companyName"],
            int(payload["totalOrderTimes"]),
            1 if bool(payload["VIP"]) else 0,
            payload["avatarURL"],
            int(payload["balance"]),
            payload["TEL"],
            c_id,
        )
        
        result, error = _execute_query(query, data)
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify({"message": "updated", "cID": c_id}), 200
        
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid data format: {str(e)}"}), 400
    except Exception as e:
        current_app.logger.error(f"update_customer error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@customer.route("/<int:c_id>", methods=["DELETE"])
def delete_customer(c_id: int):
    """Delete a customer by cID"""
    query = "DELETE FROM Customers WHERE cID=%s"
    
    rows_affected, error = _execute_query(query, (c_id,))
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({"deleted": c_id, "rows_affected": rows_affected}), 200


@customer.route("/", methods=["GET"])
def list_customers():
    """List customers with optional search functionality"""
    search_term = (request.args.get("q") or "").strip()
    
    if search_term:
        query = """
            SELECT cID, fName, lName, email, TEL
            FROM Customers
            WHERE fName LIKE %s OR lName LIKE %s OR email LIKE %s
            ORDER BY cID DESC
            LIMIT 200
        """
        like_pattern = f"%{search_term}%"
        params = (like_pattern, like_pattern, like_pattern)
    else:
        query = """
            SELECT cID, fName, lName, email, TEL 
            FROM Customers 
            ORDER BY cID DESC 
            LIMIT 200
        """
        params = None
    
    result, error = _execute_query(query, params, fetch_all=True, dictionary=True)
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify(result), 200


@customer.route("/<int:c_id>/orders", methods=["GET"])
def list_customer_orders(c_id: int):
    """List recent orders for a specific customer"""
    query = """
        SELECT o.*
        FROM Orders o
        WHERE o.cID = %s
        ORDER BY o.orderID DESC
        LIMIT 100
    """
    
    result, error = _execute_query(query, (c_id,), fetch_all=True, dictionary=True)
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify(result), 200

    
@customer.route("/<int:c_id>/funds", methods=["POST"])
def add_funds(c_id: int):
    """
    Atomically increment a customer's balance on the server side.
    Request JSON: { "amount": number > 0 }
    Returns: { cID, balance }
    """
    try:
        payload = request.get_json(silent=True) or {}
        amount = payload.get("amount", None)
        amount = float(amount)
        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400
    except Exception:
        return jsonify({"error": "Invalid amount"}), 400

    # Increment balance in a single atomic statement
    upd_sql = "UPDATE Customers SET balance = COALESCE(balance, 0) + %s WHERE cID = %s"
    updated_rows, err = _execute_query(upd_sql, (amount, c_id))
    if err:
        return jsonify({"error": err}), 500
    if not updated_rows:
        return jsonify({"error": "Customer not found"}), 404

    # Return the new balance
    sel_sql = "SELECT cID, balance FROM Customers WHERE cID = %s"
    row, err = _execute_query(sel_sql, (c_id,), fetch_one=True, dictionary=True)
    if err:
        return jsonify({"error": err}), 500

    return jsonify({"cID": row["cID"], "balance": row.get("balance", 0)}), 200
