import logging

def get_log(debug=False):
    # configure log
    log = logging.getLogger("")
    formatter = logging.Formatter("%(asctime)s %(levelname)s " +
                                  "[%(module)s] %(message)s")
    # log the things
    log.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    if debug:
        ch.setLevel(logging.DEBUG)
    else:
        ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    log.addHandler(ch)

    log.info('Start Runing...')
    return log
