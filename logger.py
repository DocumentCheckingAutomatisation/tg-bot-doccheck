import logging

FEEDBACK_LEVEL_NUM = 25
logging.addLevelName(FEEDBACK_LEVEL_NUM, "FEEDBACK")

def feedback(self, message, *args, **kws):
    if self.isEnabledFor(FEEDBACK_LEVEL_NUM):
        self._log(FEEDBACK_LEVEL_NUM, message, args, **kws)

logging.Logger.feedback = feedback

log_format = "%(asctime)s [%(levelname)s] %(message)s"
file_handler = logging.FileHandler("bot.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(log_format))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
