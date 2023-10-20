import serial	#alarm dependencies 
import serial.tools.list_ports
import time
import datetime
import pygame
import keyboard

import os
os.chdir(os.path.dirname(os.path.realpath(__file__)))

def stop_sound():
    print("stoping sound")
    pygame.mixer.music.stop()


class Alarm:
    #testing settings
    testing_bool=False
    time_inc=0.1

    #setting alarm
    prev_day=datetime.datetime.now().day
    set_hour=9
    set_minute=10
    set_time_float=set_hour+set_minute/60
    first_set_time_float=set_time_float
    prev_alarm_time=first_set_time_float

    alarm_names=["calm_alarm.mp3","jungle_sounds.mp3","insane_alarm.mp3"]
    alarm_name=alarm_names[1]
    sound_duration=0.02
    time_since_update=1
    time_tracker=time.time()
    prev_time_float=0
    current_time_float=0
    
    #snooze settings
    snooze_duration=0.15
    snooze_count=0
    snooze_enabled=True
    alarm_count=0



    #arduino data
    button_bool=False
    button_bool_prev=False
    motion_bool=False
    motion_bool_prev=False
    #motion settings
    motion_count_prev=0
    current_motion_count=0
    active_motion_bool=False
    motions_before_active=2
    motion_based_soft_wakeup_duration=0.25


    #alarm settings and states
    in_zone=False
    in_zone_prev=True
    zone_duration_float=1

    sound_active=False

    stop_key=False

    start_alarm=False
    start_alarm_prev=False



    #motion sentry
    motion_sentry_mode=False
    motion_sentry_pauseduration=0.02


    def update(self):
        #update time
        t_s=datetime.datetime.now()
        self.time_since_update=time.time()-self.time_tracker
        self.time_tracker=time.time()
        #check if testing bool is active
        if self.testing_bool>0:
            self.current_time_float+=self.time_inc*self.time_since_update
            if not self.in_zone:
                self.time_inc=0.5
            else:
                self.time_inc=0.01
        else:
            self.current_time_float=t_s.hour+t_s.minute/60
        #reset alarm if it is the next day
        if (t_s.day!=self.prev_day) or (self.testing_bool and (self.current_time_float>24)):
            if self.testing_bool:
                self.current_time_float=0
            self.alarm_count=0
            self.snooze_count=0
            self.alarm_name=self.alarm_names[1]
            self.motion_sentry_mode=False
            self.current_motion_count=0
            self.motion_count_prev=0
            self.snooze_duration=0.15
            self.set_time_float=self.first_set_time_float
        self.prev_time_float=self.current_time_float

        #zone
        self.in_zone=(self.current_time_float>=self.first_set_time_float) and (self.current_time_float<(self.first_set_time_float+self.zone_duration_float))


        #motion upon zone
        if (self.in_zone and not self.in_zone_prev):#calculate motion counts
            self.motion_count_prev=self.current_motion_count
        self.active_motion_bool=((self.motion_count_prev+self.motions_before_active)<self.current_motion_count)
        

        #Alarming logic
        if self.in_zone:
            if not self.motion_sentry_mode:
                #activate first alarm
                if (self.alarm_count==0):
                    self.start_alarm=(self.active_motion_bool or (self.current_time_float>(self.first_set_time_float+self.motion_based_soft_wakeup_duration)))
                else:
                    self.start_alarm=self.current_time_float>self.set_time_float
            #Sentry Mode
            else:
                #if it is time to turn on motion sentry
                if ((self.prev_alarm_time+self.motion_sentry_pauseduration)<self.current_time_float):
                    if self.active_motion_bool:
                        self.start_alarm=True
                else:
                    self.motion_count_prev=self.current_motion_count

        #Snoozer Scheduler
        if self.start_alarm:
            self.prev_alarm_time=self.current_time_float
            self.alarm_count+=1

            if self.alarm_count==2: 
                self.snooze_duration=0.08
            elif self.alarm_count==3:
                self.snooze_duration=0.03
            elif self.alarm_count==7:
                self.alarm_name=self.alarm_names[1]

            if self.alarm_count>3:
                self.snooze_enabled=False
            else:
                self.snooze_enabled=True

            self.set_time_float=self.current_time_float+self.snooze_duration
        

        ##Mixer update
        #Start Alarm
        if self.start_alarm:
            pygame.mixer.music.load(self.alarm_name)
            pygame.mixer.music.play(-1)
            self.sound_active=True
        
        #Stop if outsize zone
        if not self.in_zone:
            if self.sound_active:
                stop_sound()
                self.sound_active=False

        
        #Stop if stop_key is pressed
        if self.stop_key:
            if self.sound_active:
                stop_sound()
                self.sound_active=False

        #Stop if sound duration is exceeded
        if ((self.prev_alarm_time+self.sound_duration)<self.current_time_float):
            if self.sound_active:
                print("duration exceeded")
                stop_sound()
                self.sound_active=False
        
        #If snooze is pressed
        if (not self.motion_sentry_mode) and self.snooze_enabled and (self.button_bool and not self.button_bool_prev):
            if self.sound_active:
                stop_sound()
                self.sound_active=False
            self.snooze_count+=1
        

        print("start alarm: ",self.start_alarm, " time float: ", self.current_time_float, " alarm set point: ", self.set_time_float, " in zone: ",self.in_zone)

        #variable updates
        self.start_alarm=False
        self.button_bool_prev=self.button_bool
        self.motion_bool_prev=self.motion_bool
        self.in_zone_prev=self.in_zone
        self.start_alarm_prev=self.start_alarm
        self.prev_day=t_s.day





def main():
    #Connect to arduino
    ports = serial.tools.list_ports.comports()
    arduino_port=""
    for port in ports:
        if (port.vid==9025 and port.pid==67):
                print(port.description, " is an arduino")
                arduino_port=port.device
        else:
            print(port.description)
    arduino_port="COM3"
    try:
        ser=serial.Serial(arduino_port,9600,timeout=0.1)#,parity=serial.PARITY_EVEN, rtscts=1)
        print("connected to: ", ser.portstr)
    except Exception as ec:
        print(ec)


    #alarm sounds setup
    pygame.init()
    pygame.mixer.init()

    alarm=Alarm()

    #initialization of variables
    arduino_num=0



    #If testing get settings to test
    with open("settings.txt","r") as sf:
        alarm.testing_bool=int(sf.readline().split(":")[-1])
        if alarm.testing_bool:
            alarm.current_time_float=float(sf.readline().split(":")[-1])
            print("ctf: ",alarm.current_time_float)
            alarm.time_inc=float(sf.readline().split(":")[-1])
            print("time inc: ",alarm.time_inc)
            alarm.first_set_time_float=alarm.set_time_float
            alarm.prev_alarm_time=alarm.first_set_time_float

    #Start main loop
    while True:
        #sleep for half second
        time.sleep(0.5)
        
        #gets arduino data
        try:
            data=ser.read(2048)
            s_data=data[-10:]
            for i in range(10):
                if (s_data[i]==10):
                    arduino_num=10*(s_data[i+1]-48)+(s_data[i+2]-48)
                    break
            ser.flushInput()
        except Exception as e:
            #print(e)
            alarm.button_bool=False
            arduino_num=12
        #record motion
        if ((1-arduino_num%2) and not alarm.motion_bool_prev):
            print("MOTION")
            f_r=open("motion_record.txt","r+")
            f_r.seek(0,2)
            f_r.write(str("\n"+str(datetime.datetime.now())))
            f_r.close()

        #set alarm arduino data
        alarm.motion_bool=1-arduino_num%2
        alarm.button_bool=((int(arduino_num/10)-1)>0)


        #check if spacebar is pressed to go to sentry motion mode
        if keyboard.is_pressed('space'):
            print("Alarm in motion sentry mode")
            alarm.motion_sentry_mode=True
            alarm.stop_key=True
        else:
            alarm.stop_key=False
        if keyboard.is_pressed("m"):
            alarm.current_motion_count+=1
            print("motion button")
        if keyboard.is_pressed("b"):
            alarm.button_bool=True
            print("button pressed")


        #update alarm
        alarm.update()



if __name__ == "__main__":
    main()