import logging
import papermill as pm
import ray
from ray import serve
import signal
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

NST_PIPELINE_NOTEBOOK = "https://github.com/pgagarinov/pytorch-hyperlight/raw/0.2.6/products/examples/plain_simple_nst.ipynb"

BUCKET_NAME = "sagemaker-eu-west-1-67785632"
RESOURCES_CONFIG = {"num_gpus": 1}


def transfer_style(flask_request):
    logger.critical("style transfer: started")

    all_param_dict = flask_request.json
    logger.critical(f"input params: {all_param_dict}")

    assert all_param_dict["MODEL_NAME"] == "plain_nst"

    nb_param_dict = {
        k: v for k, v in all_param_dict.items() if k != "RESULTED_NOTEBOOK_PATH_OR_URL"
    }
    logger.critical("execution of the notebook: started")

    obj_ref = ray.remote(num_gpus=1)(pm.execute_notebook).remote(
        NST_PIPELINE_NOTEBOOK,
        all_param_dict["RESULTED_NOTEBOOK_PATH_OR_URL"],
        nb_param_dict,
    )
    _ = ray.get(obj_ref)

    logger.critical("execution of the notebook: done")
    logger.critical("style transfer: done")
    return "Ok"


def signal_handler(sig, frame):
    print('Server is stopped, you pressed Ctrl+C!')
    sys.exit(0)


if __name__ == "__main__":

    ray.shutdown()
    _ = ray.init(num_cpus=8, num_gpus=1)

    HTTP_OPTIONS = {
        'host': '0.0.0.0',
        'port': 8000
    }

    client = serve.start(http_host=HTTP_OPTIONS['host'], http_port=HTTP_OPTIONS['port'])

    client.create_backend(
        "style-transfer-backend", transfer_style
        #, ray_actor_options=RESOURCES_CONFIG
    )

    client.create_endpoint(
        "style-transfer-endpoint",
        backend="style-transfer-backend",
        route="/run-style-transfer",
        methods=["GET"],
    )
    signal.signal(signal.SIGINT, signal_handler)
    print('Server is running... press Ctrl+C to stop it if needed.')
    signal.pause()