# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
sys.path.insert(0, "/opt/aldebaran/lib/python2.7/site-packages")

from naoqi import ALProxy

IP   = "127.0.0.1"
PORT = 9559

def main():
    tts      = ALProxy("ALTextToSpeech",  IP, PORT)
    animated = ALProxy("ALAnimatedSpeech", IP, PORT)
    leds     = ALProxy("ALLeds",          IP, PORT)
    motion   = ALProxy("ALMotion",        IP, PORT)
    posture  = ALProxy("ALRobotPosture",  IP, PORT)

    tts.setLanguage("Japanese")
    motion.wakeUp()
    posture.goToPosture("Stand", 0.5)

    leds.fadeRGB("FaceLeds", 1.0, 0.9, 0.0, 0.3)
    animated.say(
        "^start(animations/Stand/Gestures/Hey_1) "
        "\xe3\x81\x93\xe3\x82\x93\xe3\x81\xab\xe3\x81\xa1\xe3\x81\xaf\xef\xbc\x81"
        "\xe3\x82\x8f\xe3\x81\x9f\xe3\x81\x97\xe3\x81\xaf\xe3\x83\x9a\xe3\x83\x83\xe3\x83\x91\xe3\x83\xbc\xe3\x81\xa7\xe3\x81\x99\xe3\x80\x82"
        "\xe3\x82\x88\xe3\x82\x8d\xe3\x81\x97\xe3\x81\x8f\xe3\x81\x8a\xe9\xa1\x98\xe3\x81\x84\xe3\x81\x97\xe3\x81\xbe\xe3\x81\x99\xef\xbc\x81"
        "^wait(animations/Stand/Gestures/Hey_1)"
    )

    leds.fadeRGB("FaceLeds", 1.0, 1.0, 1.0, 0.5)
    posture.goToPosture("Stand", 0.5)
    print("done")

if __name__ == "__main__":
    main()
