# Telegram bot for Neural Style Transfer

<img width="500px" src="https://user-images.githubusercontent.com/4868370/107161449-d5abd900-69ad-11eb-80cf-af107cb81c0c.gif">

## Features

### Two style transfer models
 #### Multi-style NST
 A multi-style version of NST capable of transferring style from multiple source images (with equal weights by default). The original plain NST algorithm [[1]](#1) has been modified to transfer styles from multiple images, the implementation uses [PyTorch Hyperlight](https://github.com/pgagarinov/pytorch-hyperlight) micro ML framework. Please refer to this [Multi-style NST Jupyter notebook](https://github.com/pgagarinov/dls-style-telegram-bot/blob/main/ml_server/plain_simple_nst.ipynb) for implementation details.
 
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
 
 
 ## Deployment
 ### Telegram bot
 The bot is deployed in [Heroku](www.heroku.com) cloud application platform with a free (personal) plan. 
 
 https://github.com/pgagarinov/pytorch-hyperlight/blob/main/products/jupyterlab-ml-devenv/README.md
  
  ### ML server
 - The ML server runs on a physical Linux (Manjaro Linux) server with GeForce GTX 970 4Gb GPU.  [ml_server](/ml_server) subfolder of this repo contains bash scripts for running the server via [GNU Screen](https://www.man7.org/linux/man-pages/man1/screen.1.html) utility from under specified conda environment. Conda environment expects to contain all necessary dependencies which can either be installed via `pip install -r ./requirements.txt` or via following the instructions from [PyTorch HyperLight ML Development Environment](https://github.com/pgagarinov/pytorch-hyperlight/blob/main/products/jupyterlab-ml-devenv/README.md) project. The latter assumes you run Arch Linux or its derivative (like Manjaro Linux).
 
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
