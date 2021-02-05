# DLSchool Telegram bot for Neural Style Transfer

## Features
 - A multi-style version of NST capable of transferring style from multiple source images (with equal weights by default). The original plain NST algorithm [[1]](#1) has been modified to transfer styles from multiple images, the implementation uses [PyTorch Hyperlight](https://github.com/pgagarinov/pytorch-hyperlight) micro ML framework. Please refer to this [Multi-style NST Jupyter notebook](https://github.com/pgagarinov/dls-style-telegram-bot/blob/main/ml_server/plain_simple_nst.ipynb) for implementation details.
 
 - Pretrained CycleGan-based NST for the following styles:
    - Summer to winter
    - Winter to summer
    - Monet
    - Cezanne
    - Ukiyoe
    - Vangogh
    
    The implementation is based on [pytorch-CycleGAN-and-pix2pix](https://github.com/junyanz/pytorch-CycleGAN-and-pix2pix) ![](https://img.shields.io/github/stars/junyanz/pytorch-CycleGAN-and-pix2pix.svg?style=social) and [[2]](#2), [[3]](#3).
   
 ## Architecture
 The bot is implementation is based on [AIOGram](https://aiogram.dev/) fully asynchronous framework for Telegram Bot API. ML models run in a separate ML serving server based on [Ray serve](https://docs.ray.io/en/master/serve/index.html) scalable model serving library built on [Ray](https://ray.io/). 
 
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
