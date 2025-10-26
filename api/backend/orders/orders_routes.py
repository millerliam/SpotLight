from flask import Blueprint, request, jsonify, current_app
from backend.db_connection import db
from mysql.connector import Error


orders = Blueprint("orders", __name__)


@orders.route("/processed_orders", methods=["GET"])
def list_processed_orders():
    try:
        cursor = db.get_db().cursor()
        cursor.execute(
            (
                "SELECT orderID, processTime, processorID "
                "FROM ProcessedOrder ORDER BY processTime DESC, orderID DESC"
            )
        )
        data = cursor.fetchall()
        cursor.close()
        return jsonify(data), 200
    except Error as e:
        current_app.logger.error(f"list_processed_orders error: {e}")
        return jsonify({"error": str(e)}), 500


@orders.route("/orders", methods=["GET"])
def list_orders():
    try:
        c_id = request.args.get("cID")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        query = "SELECT orderID, date, total, cID FROM Orders WHERE 1=1"
        params = []
        if c_id:
            query += " AND cID = %s"
            params.append(c_id)
        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)
        query += " ORDER BY date DESC, orderID DESC"

        cursor = db.get_db().cursor()
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        return jsonify(rows), 200
    except Error as e:
        current_app.logger.error(f"list_orders error: {e}")
        return jsonify({"error": str(e)}), 500


@orders.route("/orders", methods=["POST"])
def create_order():
    try:
        payload = request.get_json(silent=True) or {}
        required = ["cID", "date"]
        missing = [f for f in required if f not in payload]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        cursor = db.get_db().cursor()
        cursor.execute(
            "INSERT INTO Orders (date, total, cID) VALUES (%s, %s, %s)",
            (payload["date"], payload.get("total", 0), payload["cID"]),
        )
        new_id = cursor.lastrowid
        # Mark as unprocessed (pre-processing)
        cursor.execute(
            "INSERT INTO ToBeProcessedOrder (orderID, status) VALUES (%s, %s)",
            (new_id, "in_chart"),
        )
        db.get_db().commit()
        cursor.close()
        return jsonify({"message": "created", "orderID": new_id}), 201
    except Error as e:
        current_app.logger.error(f"create_order error: {e}")
        return jsonify({"error": str(e)}), 500


@orders.route("/orders", methods=["PUT"])
def update_order_start_date():
    try:
        payload = request.get_json(silent=True) or {}
        required = ["orderID", "date"]
        missing = [f for f in required if f not in payload]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        cursor = db.get_db().cursor()
        # Only allow update if order is unprocessed
        cursor.execute(
            "SELECT 1 FROM ToBeProcessedOrder WHERE orderID = %s",
            (payload["orderID"],),
        )
        row = cursor.fetchone()
        if not row:
            cursor.close()
            return jsonify({"error": "Order is already processed or does not exist"}), 400

        cursor.execute(
            "UPDATE Orders SET date = %s WHERE orderID = %s",
            (payload["date"], payload["orderID"]),
        )
        db.get_db().commit()
        cursor.close()
        return jsonify({"message": "updated", "orderID": payload["orderID"]}), 200
    except Error as e:
        current_app.logger.error(f"update_order_start_date error: {e}")
        return jsonify({"error": str(e)}), 500


@orders.route("/orders", methods=["DELETE"])
def delete_unprocessed_order():
    try:
        order_id = request.args.get("orderID")
        if not order_id:
            return jsonify({"error": "Missing orderID"}), 400

        cursor = db.get_db().cursor()
        # Ensure unprocessed
        cursor.execute(
            "SELECT 1 FROM ToBeProcessedOrder WHERE orderID = %s",
            (order_id,),
        )
        row = cursor.fetchone()
        if not row:
            cursor.close()
            return jsonify({"error": "Order is already processed or does not exist"}), 400

        cursor.execute("DELETE FROM Orders WHERE orderID = %s", (order_id,))
        db.get_db().commit()
        cursor.close()
        return jsonify({"message": "deleted", "orderID": int(order_id)}), 200
    except Error as e:
        current_app.logger.error(f"delete_unprocessed_order error: {e}")
        return jsonify({"error": str(e)}), 500


@orders.route("/orders/<int:order_id>", methods=["GET"])
def get_order(order_id: int):
    try:
        cursor = db.get_db().cursor()
        cursor.execute(
            "SELECT orderID, date, total, cID FROM Orders WHERE orderID = %s",
            (order_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return jsonify({"error": "Order not found"}), 404
        return jsonify(row), 200
    except Error as e:
        current_app.logger.error(f"get_order error: {e}")
        return jsonify({"error": str(e)}), 500


@orders.route("/to_be_processed_order", methods=["GET"])
def list_to_be_processed_orders():
    try:
        cursor = db.get_db().cursor()
        cursor.execute(
            "SELECT orderID, status FROM ToBeProcessedOrder ORDER BY orderID DESC"
        )
        data = cursor.fetchall()
        cursor.close()
        return jsonify(data), 200
    except Error as e:
        current_app.logger.error(f"list_to_be_processed_orders error: {e}")
        return jsonify({"error": str(e)}), 500

