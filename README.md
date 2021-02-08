# Telegram bot for Neural Style Transfer

<img width="500px" src="https://user-images.githubusercontent.com/4868370/107161449-d5abd900-69ad-11eb-80cf-af107cb81c0c.gif">

## Features

### Two different style transfer models
implemented as parameterized Jupyter Notebooks executed via [Papermill](https://github.com/nteract/papermill) library:
#### Multi-style NST
 A multi-style version of NST capable of transferring style from multiple source images (with equal weights by default). The styled image is found via training the Deep Neural Network match the styled of the found (styled) image to the style of the style source image as closely as possible (without deviating from the content image in terms of content). The implementation is based on [PyTorch Hyperlight](https://github.com/pgagarinov/pytorch-hyperlight) micro ML framework and uses the algorithm from "A Neural Algorithm of Artistic Style" [[1]](#1) paper with a few modifications:
  - style can be transferred from an arbitrary number of style source images (giving equal weights to each style), not just one
  - different layers of VGG19 are used for more realistic style transfer
  - an early stopping is used for choosing the number of epochs automatically

Please refer to this [Multi-style NST Jupyter notebook](https://github.com/pgagarinov/dls-style-telegram-bot/blob/main/ml_server/plain_simple_nst.ipynb) for more details.

 
#### Pretrained CycleGAN-based NST
- Pretrained CycleGan-based NST for the following styles:
   - Summer to winter
   - Winter to summer
   - Monet
   - Cezanne
   - Ukiyoe
   - Vangogh
    
    The corresponding image processing pipeline is implemented in [CycleGan Style transfer notebook](https://github.com/pgagarinov/dls-style-telegram-bot/blob/main/ml_server/cycle_gan_style_inference.ipynb) and is based on [pytorch-CycleGAN-and-pix2pix](https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix) ![](https://img.shields.io/github/stars/junyanz/pytorch-CycleGAN-and-pix2pix.svg?style=social) and [[2]](#2), [[3]](#3).
 
### Finite-state machine with in-memory storage
The bot uses Finite State Machine with in-memory storage to keep the running costs low. Some cloud providers, like Heroku, can put the container running the but to sleep after some period of inactivity (30 mintues for Heroku). This causes the bot to lose its in-memory state after sleep. This is not critical however, as the bot can always wake up in the initial state without making the user experience much worse. When the bot looses its state it notifies a user about it asking for a content image regardless of what happened before the period of inactivity.
 
### Automatic image resizing
The high-resolution images are scaled down before they are processed by NST models. As the result the styled (output) usually has lower resolution comparing to the input image. This is a necessary evil which allows for faster NST and lower GPU memory requirements.
 
  
## Architecture
The high level architecture is show below.

<img src="https://user-images.githubusercontent.com/4868370/107093369-2c7eaa80-6816-11eb-8f37-e1b9c8f55f47.png" width="500">

### Telegram bot
The bot is implementation is based on [AIOGram](https://aiogram.dev/) fully asynchronous framework for Telegram Bot API. [AIOGram Finite State Machine (FSM)](https://docs.aiogram.dev/en/latest/examples/finite_state_machine_example.html) is used to improve the source code structure. FSM uses in-memory storage to keep the running costs minimal. The in-memory storage can be easily replaced with either Redis, RethinkDB, MongoDB (see https://docs.aiogram.dev/en/latest/dispatcher/fsm.html) if needed.
 
### ML server
ML models run in a separate ML serving backend based on [Ray Serve](https://docs.ray.io/en/master/serve/index.html) scalable model serving library built on [Ray](https://ray.io/). ML server receives the image processing requests via REST API from the bot and forwards them to Jupyter notebooks via [Papermill](https://github.com/nteract/papermill) library. Each notebook is responsible for a model-specific ML image processing pipeline.  Each of the notebooks contains an ML model-specific image processing pipeline and can be found [here](https://github.com/pgagarinov/dls-style-telegram-bot/tree/main/ml_server). The notebooks have a direct access to S3 cloud, they download images from S3 and upload the processed images back to S3. ML server tracks the execution of the notebooks via [Papermill](https://github.com/nteract/papermill) and uploads the executed notebooks to S3 bucket upon completion. The failed notebooks are kept in S3 for easier debugging (intil S3's built-in retention removes them).
 
 
### Cloud Object Storage
Amazon S3 is used for transferring the photos from the bot to ML server and back. Such approach allows easier debugging comparing to sending images as part of REST API requests 
directly to ML server.

## Configuration
### Telegram bot
The bot expects the following groups of environment variables to be defined
#### Telegram integration settings
- `API_TOKEN` - the bot token generated by Telegram's @BotFather
- `WEBHOOK_HOST_ADDR` - the bot endpoint url exposed to Telegram
- `PORT` - the port for bot endpoint url exposed to Telegram

#### S3 integration settings
- `S3_BUCKET_WITH_RESULTS_NAME` - S3 bucket name
- `S3_RESULTS_PREFIX` - S3 bucket folder name
- `AWS_ACCESS_KEY_ID` - [AWS access key id](https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html#access-keys-and-secret-access-keys)
- `AWS_SECRET_ACCESS_KEY` - [AWS access key](https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html#access-keys-and-secret-access-keys)
- `REGION_NAME` - [AWS region name](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#concepts-regions)

 
#### ML settings
- `ML_SERVER_HOST_ADDR` - URL of ML server endpoint exposed to the bot
- `DEFAULT_FAST_DEV_RUN` - can take "True"/"False" values; enables a faster regime for ML models (with a limited number of training epochs and less number of batches in an epoch) for debugging purposes

 
 
 ## Deployment
 ### Telegram bot
 The bot can be deployed in both cloud and physical environments. The following deployment scenarios were tested:
  - Cloud deployment on [Heroku](www.heroku.com) cloud application platform as well as. [telegram_bot](/telegram_bot) folder of this repo contains all necessary files for Heroku deployment. When pushing the source code to Heroku repo for deployment make sure to push only [telegram_bot](telegram_bot) subfolder via running 
  ```bash
  git push heroku `git subtree split --prefix telegram_bot main`:master
  ```
  (otherwise you would push the whole repo and Heroku won't find the files necessary for deployment). Please refer to [Heroku: getting started with Python](https://devcenter.heroku.com/articles/getting-started-with-python) for details. 
  - On-prem deployment via exposing the bot's webhook URL to Telegram via NGINX.
 
 https://github.com/pgagarinov/pytorch-hyperlight/blob/main/products/jupyterlab-ml-devenv/README.md
  
  ### ML server
  Tested deployment scenarios:
  - On-prem deployment on a physical Linux (Manjaro Linux) server with GeForce GTX 970 4Gb GPU.  [ml_server](/ml_server) folder of this repo contains bash scripts for running the server via [GNU Screen](https://www.man7.org/linux/man-pages/man1/screen.1.html) utility from under specified conda environment. Conda environment expects to contain all necessary dependencies which can either be installed via `pip install -r ./requirements.txt` or via following the instructions from [PyTorch HyperLight ML Development Environment](https://github.com/pgagarinov/pytorch-hyperlight/blob/main/products/jupyterlab-ml-devenv/README.md) project. The latter assumes you run Arch Linux or its derivative (like Manjaro Linux). 
  
  - Cloud deployment via [Amazon Sagemaker Python SDK](https://sagemaker.readthedocs.io/en/stable/) with GPU-powered ml.p2.xlarge instance and PyTorch 1.5. In this scenario only a limited functionality of ML server (CycleGANs only) is available as the multi-style NST implementation used by ML server requires at least PyTorch 1.7. At the time of writing this  the most recent version of PyTorch supported by the pre-build Amazon Sagemaker containers is 1.6. Amazon has recently released a [deep learning container for PyTorch 1.7.1](https://github.com/aws/deep-learning-containers/releases/tag/v1.0-pt-1.7.1-tr-py36) but at the time of writing this the container is not yet available in Sagemaker Python SDK. The PyTorch 1.5 container was used for testing instead of PyTorch 1.6 container because the latter behaved less stably. 
     
 ## References
 <a id="1">[1]</a> 
 "A Neural Algorithm of Artistic Style", Gatys, Leon A.; Ecker, Alexander S.; Bethge, Matthias, 2015, [arXiv:1508.06576](https://arxiv.org/abs/1508.06576) 

 <a id="2">[2]</a> 
  "Unpaired Image-to-Image Translation using Cycle-Consistent Adversarial Networkss", Zhu, Jun-Yan and Park, Taesung and Isola, Phillip and Efros, Alexei A
    Computer Vision (ICCV), 2017 IEEE International Conference on, 2017

 <a id="3">[3]</a> 
  "Image-to-Image Translation with Conditional Adversarial Networks",
  Isola, Phillip and Zhu, Jun-Yan and Zhou, Tinghui and Efros, Alexei A,
  Computer Vision and Pattern Recognition (CVPR), 2017 IEEE Conference on,
  2017
