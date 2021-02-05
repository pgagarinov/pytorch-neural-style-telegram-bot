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
   
 
 
 ## References
 <a id="1">[1]</a> 
 Gatys, Leon A.; Ecker, Alexander S.; Bethge, Matthias (26 August 2015). "A Neural Algorithm of Artistic Style". [arXiv:1508.06576](https://arxiv.org/abs/1508.06576) 

