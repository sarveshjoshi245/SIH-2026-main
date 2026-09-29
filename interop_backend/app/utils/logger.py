import logging
import json
import datetime


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        if hasattr(record, "transaction_id"):
            log_obj["transaction_id"] = record.transaction_id
        if hasattr(record, "extra_data"):
            log_obj["data"] = record.extra_data
        return json.dumps(log_obj)


def get_logger(name: str = "interop_platform") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
