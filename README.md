# PiCam API

## Simple Raspberry Pi Zero 2W  Camera Flask REST-API and makes use of libcamera2

This project is still under `development` but works as POC!!!  

This will be used with the [Front_Door_Intercom_automation](https://github.com/OliverDrechsler/front_door_intercom_automation) Github Porject to take a photo.

ToDo's:

- [ ] rework code docu
- [ ] create build and test pipelines
- [ ] docu
- [ ] unit tests

## How to install

```
apt install libcap-dev libcap2-bin  libcap2

sudo apt install -y python3-libcamera python3-kms++
sudo apt install -y python3-prctl libatlas-base-dev ffmpeg libopenjp2-7
pip3 install numpy --upgrade
pip3 install picamera2

python3 -m venv --system-site-packages .venv
```
Further you can foolow the [How to do a fresh installtion on RPi with code](How_to_install_fresh_RPi_with_code.md)

### System service setup
Edit file `picam.service` and adjust to your path ( `ExecStart=/usr/local/bin/PiCam_API_2......` ).  
To run fdia as a service on startup with root permissions  
copy `picam.service`to `/etc/systemd/system/`to your RPi systemd deamon folder.  
Run `systemctl daemon-reload` and `systemctl start fdia`to start it as a service.  
Enable system service with `systemctl enable picam.service`.

### Camera lifetime and exposure logging

When `foto_api.py` is started, the camera is configured at `640x480` and its
stream remains active for the lifetime of the process. A photo request only
captures a frame. If a request asks for a different resolution, the camera is
briefly reconfigured and then remains running at that resolution.

For every saved image the application log records the values actually used by
libcamera, for example:

```
Captured frame: ExposureTime=12345 us, AnalogueGain=1.0, DigitalGain=1.0, FrameDuration=33333 us
```

`exposure: "auto"` enables auto exposure; a numeric value disables it and sets
`ExposureTime` in microseconds. `iso: 0` retains automatic gain; other ISO
values are translated approximately to libcamera's `AnalogueGain` (`ISO / 100`).

## How to run unit-tests
`pytest --cov=./ --cov-report=html`
