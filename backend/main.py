from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import db_helper
import generic_helper

app = FastAPI()

inprogress_orders = {}

@app.post("/")
async def handle_request(request: Request):
    # Retrieve the JSON data from the request
    payload = await request.json()

    # Extract necessary information
    intent = payload.get('queryResult', {}).get('intent', {}).get('displayName', "")
    parameters = payload.get('queryResult', {}).get('parameters', {})
    output_contexts = payload.get('queryResult', {}).get('outputContexts', [])

    session_id = generic_helper.extract_session_id(output_contexts[0]['name'])

    # creating a routing table
    intent_handler_dict = {
        'new.order': new_order,
        'order.add -  context: ongoing-order': add_to_order,
        'order.remove - context: ongoing-order': remove_from_order,
        'order.complete - context:ongoing-order': complete_order,
        'track.order - context: ongoing-tracking': track_order
    }

    response = intent_handler_dict[intent](parameters, session_id)

    if response:
        return JSONResponse(content={
            "fulfillmentText": response
        })

    # Check if intent is "track.order" and context contains "ongoing-tracking"
    # if intent == "track.order - context: ongoing-tracking":
    #     response = track_order(parameters)
    #     return JSONResponse(content={
    #         "fulfillmentText": response
    #     })
    # elif intent == "order.add":

    # elif intent == "order.remove":

    # elif intent == "order.complete - context:ongoing-order":


    return JSONResponse(content={"message": "Intent not recognized"})


def new_order(parameters: dict, session_id: str):
    inprogress_orders[session_id] = {}
    fulfillment_text = "Got it! I've started a new order for you :) "\
          "What would you like to add?"


def add_to_order(parameters: dict, session_id: str):
    food_items = parameters["food-item"]
    numbers = parameters["number"]

    # all food items should have quantity with them
    if(len(food_items) != len(numbers)):
        fulfillment_text = "Sorry I didn't understand. Can you please specify the food items and quantities of each item correctly!"
    else:
        new_food_dict = dict(zip(food_items, numbers))
        
        if session_id in inprogress_orders:
            current_food_dict = inprogress_orders[session_id]
            current_food_dict.update(new_food_dict)
            inprogress_orders[session_id] = current_food_dict
        else:
            inprogress_orders[session_id] = new_food_dict
        
        order_str = generic_helper.get_string_from_food_dict(inprogress_orders[session_id])
        fulfillment_text = f"So far you have {order_str}. Would you like to add anything else?"

    return fulfillment_text



def remove_from_order(parameters: dict, session_id):

    if session_id not in inprogress_orders:
        fulfillment_text = "I'm having trouble finding your order :( " \
              "Sorry! Please place your order again."
    else:
        current_order = inprogress_orders[session_id]
        food_items = parameters["food-item"]
        removed_items = []
        no_such_items = []
        for item in food_items:
            if item not in current_order:
                no_such_items.append(item)
            else:
                removed_items.append(item)
                del current_order[item]
        
        if len(food_items) > 0:
            fulfillment_text = f"Sure! Removed {",".join(removed_items)} from your order! "

        if len(no_such_items) > 0:
            fulfillment_text = f"Your current order does not have {",".join(removed_items)}! "

        if len(current_order.keys()) == 0:
            fulfillment_text += "Your order is empty :( "
        else:
            order_str = generic_helper.get_string_from_food_dict(current_order)
            fulfillment_text += f"Here's what's left in your order: {order_str}"

    return fulfillment_text



def complete_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        fulfillment_text = "I'm having trouble finding your order :(" \
              "Sorry! Please place your order again."
    else:
        order = inprogress_orders[session_id]
        newly_created_order_id = save_to_db(order)
        if newly_created_order_id == -1:
            fulfillment_text = "Sorry! Couldn't place your order due to some technical issues :( " \
                  "Please try to place your order again!"
        else:
            order_total = db_helper.get_total_order_price(newly_created_order_id)
            fulfillment_text = f"Hooray! Your order is placed!! :) " \
                  f"Here's your order id: {newly_created_order_id}. " \
                  f"Your total is ${order_total} which you can pay at the time of delivery!"
        
        del inprogress_orders[session_id]

    return fulfillment_text


def save_to_db(order: dict):
    # order = {"pizza": 2, "mango lassi": 1}
    next_order_id = db_helper.get_next_order_id()
    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(
            food_item,
            quantity,
            next_order_id
        )
        
        if rcode == -1:
            return -1
        
    db_helper.insert_order_tracking(next_order_id, "in progress")
    return next_order_id



def track_order(parameters: dict, session_id: str):
    order_id = int(parameters['order_id'])

    # calling DB
    order_status = db_helper.get_order_status(order_id)

    if order_status:
        fulfillment_text = f"The order status for order id {order_id} is {order_status}"
    else:
        fulfillment_text = f"No order found with order id {order_id} :("

    return fulfillment_text
