# PiCam API

## Simple Raspberry Pi Zero Camera Flask REST-API

This project is still under `dev`!!!  

This will be used with the [Front_Door_Intercom_automation](https://github.com/OliverDrechsler/front_door_intercom_automation) Github Porject to take a photo.

ToDo's:

- [ ] docu
- [ ] unit tests
- [ ] rework code docu
- [ ] docu raspberry pi image setup




install 
apt install libcap-dev libcap2-bin  libcap2

sudo apt install -y python3-libcamera python3-kms++
sudo apt install -y python3-prctl libatlas-base-dev ffmpeg libopenjp2-7
pip3 install numpy --upgrade
pip3 install picamera2

python3 -m venv --system-site-packages .venv


### System service setup
Edit file `picam.service` and adjust to your path ( `ExecStart=/usr/local/bin/PiCam_API_2......` ).  
To run fdia as a service on startup with root permissions  
copy `picam.service`to `/etc/systemd/system/`to your RPi systemd deamon folder.  
Run `systemctl daemon-reload` and `systemctl start fdia`to start it as a service.  
Enable system service with `systemctl enable picam.service`.