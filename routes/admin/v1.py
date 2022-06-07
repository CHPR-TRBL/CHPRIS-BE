import logging

logger = logging.getLogger(__name__)

from Configs import baseConfig
config = baseConfig()
api = config["API"]
cookie_name = api['COOKIE_NAME']

from flask import Blueprint, request, jsonify
v1 = Blueprint("admin_v1", __name__)

from security.cookie import Cookie
from datetime import timedelta
from datetime import date
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta

from schemas.users.baseModel import users_db
from schemas.sites.baseModel import sites_db
from schemas.records.baseModel import records_db

from models.get_users import get_all_users
from models.find_users import find_user
from models.update_users import update_user
from models.create_regions import create_region
from models.create_sites import create_site
from models.data_exports import data_export

from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import Unauthorized
from werkzeug.exceptions import Conflict
from werkzeug.exceptions import Forbidden

@v1.after_request
def after_request(response):
    users_db.close()
    sites_db.close()
    records_db.close()
    return response

@v1.route("/users", methods=["GET"])
def getAllUsers():
    """
    Fetch all users.

    Body:
       None

    Response:
        200: list
        400: str
        401: str
        409: str
        403: str
        500: str
    """
    try:
        # if not request.cookies.get(cookie_name):
        #     logger.error("no cookie")
        #     raise Unauthorized()
        # elif not request.headers.get("User-Agent"):
        #     logger.error("no user agent")
        #     raise BadRequest()

        # cookie = Cookie()
        # e_cookie = request.cookies.get(cookie_name)
        # d_cookie = cookie.decrypt(e_cookie)
        # json_cookie = json.loads(d_cookie)

        # sid = json_cookie["sid"]
        # uid = json_cookie["uid"]
        # user_cookie = json_cookie["cookie"]
        # user_agent = request.headers.get("User-Agent")

        # user_id = find_session(sid, uid, user_agent, user_cookie)
        users_list = get_all_users()
        # session = update_session(sid, user_id)

        res = jsonify(users_list)
        # cookie = Cookie()
        # cookie_data = json.dumps({"sid": session["sid"], "uid": session["uid"], "cookie": session["data"]})
        # e_cookie = cookie.encrypt(cookie_data)
        # res.set_cookie(
        #     cookie_name,
        #     e_cookie,
        #     max_age=timedelta(milliseconds=session["data"]["maxAge"]),
        #     secure=session["data"]["secure"],
        #     httponly=session["data"]["httpOnly"],
        #     samesite=session["data"]["sameSite"],
        # )

        return res, 200

    except BadRequest as err:
        return str(err), 400

    except Unauthorized as err:
        return str(err), 401

    except Forbidden as err:
        return str(err), 403

    except Conflict as err:
        return str(err), 409

    except InternalServerError as err:
        logger.exception(err)
        return "internal server error", 500

    except Exception as err:
        logger.exception(err)
        return "internal server error", 500

@v1.route("/users/<int:user_id>", methods=["PUT"])
def updateUser(user_id):
    """
    Update a user's account.
    
    Parameters:
        user_id: int

    Body:
        occupation: str,
        phone_number: str,
        region_id: int,
        site_id: int,
        state: str,
        type_of_export: str,
        type_of_user: str,
        exportable_range: str

    Response:
        200: str
        400: str
        401: str
        409: str
        403: str
        500: str
    """
    try:
        user = find_user(user_id=user_id)

        payload = (
            user["id"],
            request.json["occupation"],
            request.json["phone_number"],
            request.json["region_id"],
            request.json["site_id"],
            request.json["state"],
            request.json["type_of_export"],
            request.json["type_of_user"],
            request.json["exportable_range"]
        )

        result = update_user(*payload)

        return result, 200

    except BadRequest as err:
        return str(err), 400

    except Unauthorized as err:
        return str(err), 401

    except Forbidden as err:
        return str(err), 403

    except Conflict as err:
        return str(err), 409

    except InternalServerError as err:
        logger.exception(err)
        return "internal server error", 500

    except Exception as err:
        logger.exception(err)
        return "internal server error", 500

@v1.route("/regions", methods=["POST"])
def createRegion():
    """
    Create a new region.

    Body:
        name: str,

    Response:
        200: str
        400: str
        500: str
    """
    try:
        name = request.json["name"]

        result = create_region(name=name)

        return result, 200

    except BadRequest as err:
        return str(err), 400

    except Conflict as err:
        return str(err), 409

    except InternalServerError as err:
        logger.exception(err)
        return "internal server error", 500

    except Exception as err:
        logger.exception(err)
        return "internal server error", 500

@v1.route("/regions/<int:region_id>/sites", methods=["POST"])
def createSite(region_id):
    """
    Create a new site.

    Parameters:
        region_id: int

    Body:
        name: str,

    Response:
        200: str
        400: str
        500: str
    """
    try:
        name = request.json["name"]

        result = create_site(name=name, region_id=region_id)

        return result, 200

    except BadRequest as err:
        return str(err), 400

    except Conflict as err:
        return str(err), 409

    except InternalServerError as err:
        logger.exception(err)
        return "internal server error", 500

    except Exception as err:
        logger.exception(err)
        return "internal server error", 500

@v1.route("/users/<int:user_id>/regions/<string:region_id>/sites/<string:site_id>/exports/<string:format>", methods=["GET"])
def dataExport(user_id, region_id, site_id, format):
    """
    """
    try:        
        user = find_user(user_id=user_id)

        if not user['exportable_range']:
            logger.error("Not allowed to export. Exportable_range < 1")
            raise Forbidden()
        elif user['exportable_range'] < 1:
            logger.error("Not allowed to export. Exportable_range < 1")
            raise Forbidden()
        elif not user['type_of_export']:
            logger.error("Not allowed to export. No exportation type")
            raise Forbidden()
        elif not format in user['type_of_export'].split(","):
            logger.error("Not allowed to export to %s" % format)
            raise Forbidden()

        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        month_range = date.today().month - parse(start_date).month

        logger.debug("checking exportable_range ...")
        if (month_range+1) > user['exportable_range']:
            logger.error("Not allowed to export. Exportable_range exceeded")
            raise Forbidden()

        start_date = parse(start_date)
        end_date = parse(end_date) + relativedelta(hours=23, minutes=59, seconds=59)
        req_range = end_date.month - start_date.month
                
        logger.info("requesting %d month(s) data" % (req_range+1))
        
        download_path = data_export(start_date=start_date, end_date=end_date, region_id=region_id, site_id=site_id)

        return download_path, 200

    except BadRequest as err:
        return str(err), 400

    except Unauthorized as err:
        return str(err), 401

    except Forbidden as err:
        return str(err), 403

    except Conflict as err:
        return str(err), 409

    except InternalServerError as err:
        logger.exception(err)
        return "internal server error", 500

    except Exception as err:
        logger.exception(err)
        return "internal server error", 500