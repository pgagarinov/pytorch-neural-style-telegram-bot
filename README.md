# DLSchool Telegram bot for Neural Style Transfer

## Features

### Style transfer models
 #### Multi-style NST
 A multi-style version of NST capable of transferring style from multiple source images (with equal weights by default). The original plain NST algorithm [[1]](#1) has been modified to transfer styles from multiple images, the implementation uses [PyTorch Hyperlight](https://github.com/pgagarinov/pytorch-hyperlight) micro ML framework. Please refer to this [Multi-style NST Jupyter notebook](https://github.com/pgagarinov/dls-style-telegram-bot/blob/main/ml_server/plain_simple_nst.ipynb) for implementation details.
 
 #### CycleGAN inference
 - Pretrained CycleGan-based NST for the following styles:
    - Summer to winter
    - Winter to summer
    - Monet
    - Cezanne
    - Ukiyoe
    - Vangogh
    
    The implementation is based on [pytorch-CycleGAN-and-pix2pix](https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix) ![](https://img.shields.io/github/stars/junyanz/pytorch-CycleGAN-and-pix2pix.svg?style=social) and [[2]](#2), [[3]](#3).
 
 ### No state persistency
 The bot uses Finite State Machine with in-memory storage to keep the running costs low. Some cloud providers, like Heroku, can stop the bot after some periods of inactivity. This causes the bot lose its state. This is not critical as there is no any important information in the time of inactivity between separate user interaction sessions. When the bot looses its state it notifies a user about it asking for a content image regardless of what happened before the period of inactivity.
  
 ## Architecture
 The high level architecture is show below.
 
 <img src="https://user-images.githubusercontent.com/4868370/107093369-2c7eaa80-6816-11eb-8f37-e1b9c8f55f47.png" width="500">
 
 ### Telegram bot
 The bot is implementation is based on [AIOGram](https://aiogram.dev/) fully asynchronous framework for Telegram Bot API. [AIOGram Finite State Machine (FSM)](https://docs.aiogram.dev/en/latest/examples/finite_state_machine_example.html) is used to improve the source code structure. FSM uses in-memory storage to keep the running costs minimal. The in-memory storage can be easily replaced with either Redis, RethinkDB, MongoDB (see https://docs.aiogram.dev/en/latest/dispatcher/fsm.html) if needed.
 
 ### ML server
 ML models run in a separate ML serving backend based on [Ray serve](https://docs.ray.io/en/master/serve/index.html) scalable model serving library built on [Ray](https://ray.io/). MLServer receives ML processing requests from the bot and forwards them to Jupyter notebooks. Each notebook is responsible for a separate ML model pipeline (one for CycleGAN and one for Multi-style NST). The ML server doesn't run ML models directly. Instead it forwards the processing calls to dedicated Jupyter notebooks. Each of the notebooks contains an ML model-specific image processing pipeline. Moreover, all the notebooks have the direct access to S3 cloud, download images from S3 and upload the results back. ML server tracks triggers and monitors the execution of the notebooks via [Papermill](https://github.com/nteract/papermill) library. All executed Jupyter notebooks are uploaded to S3 bucket and failed ones are kept for some time for easier debugging.
 
 
 ### Cloud Object Storage
 Amazon S3 is used for transferring the photos from the bot to ML server and back. Such approach allows easier debugging comparing to sending images as part of REST API requests 
 directly to ML server.
 
 
 ## Deployment
 The bot is deployed in [Heroku](www.heroku.com) cloud application platform. The ML server runs on-prem physical server and exposes its REST API endpoint to the bot via [NGINX](https://www.nginx.com/).
 
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
