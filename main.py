import serial	#alarm dependencies 
import serial.tools.list_ports
import time
import datetime
import sys
import os
import pygame
import keyboard

turn_off_noise=False
cancel_button=False


def main():
    #print out all available ports for arduinos
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

    alarm_names=["calm_alarm.mp3","jungle_sounds.mp3","insane_alarm.mp3"]

    selected_alarm_name=alarm_names[1]

    alarm_states=0
    alarm_h=8
    alarm_m=30

    snooze_duration=600

    alarm_wait_for_motion_minutes=15
    alarm_motion_wait=15/60

    alarm_duration=100
    
    alarm_time_float=alarm_h+alarm_m/60
    

    motion_bool=0
    motion_bool_prev=motion_bool
    motion_count=0
    motion_since_last_alarm=0
    counted_motion_bool=0
    motion_count_upon_zone=0
    arduino_num=0
    button_bool=0
    button_bool_prev=0
    alarms_count=0


    in_alarm_zone=0
    in_alarm_zone_prev=in_alarm_zone
    alarm_bool=0
    alarm_bool_prev=alarm_bool

    alarm_begin=0
    alarm_begin_prev=alarm_begin
    alarm_start_bool=0
    


    alarm_start_time=time.time()
    last_alarm_time=alarm_start_time

    t_s=datetime.datetime.now()
    time_from_alarm=t_s.hour+t_s.minute/60-alarm_time_float
    print(t_s.hour)


    pygame.init()	#alarm function
    pygame.mixer.init()


    previous_day=t_s.day
    alarm_cancel=False
    global turn_off_noise
    turn_off_noise=False
    print_time=0
    global cancel_button
    while True:
        #update time and reset at midnight
        time.sleep(0.5)
        t_s=datetime.datetime.now()
        current_time_float=t_s.hour+t_s.minute/60
        # if t_s.day!=previous_day:
        #     alarm_cancel=False
        #     turn_off_noise=False
        #     alarms_count=0
        #     selected_alarm_name=alarm_names[1]
        
        

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
            print(e)
            arduino_num=12
        motion_bool=1-arduino_num%2
        button_bool=int(arduino_num/10)-1

        

        #button snooze
        if button_bool and not button_bool_prev:
            pygame.mixer.music.stop()

        

        #record motion
        if (motion_bool and not motion_bool_prev):
            motion_count+=1
            print("MOTION")
            f_r=open("motion_record.txt","r+")
            f_r.seek(0,2)
            f_r.write(str("\n"+str(datetime.datetime.now())))
            f_r.close()
        


        #check if spacebard is pressed
        if keyboard.is_pressed('space'):
            print("Alarm Cancelled")
            alarm_cancel=True
            turn_off_noise=True
        if keyboard.is_pressed("m"):
            motion_count+=1
            print(motion_count)
        if keyboard.is_pressed("b"):
            button_bool=1
            print("button pressed")

        
        
        if ((current_time_float>=alarm_time_float) and (current_time_float<(alarm_time_float+1))):#if in time zone
            in_alarm_zone=1
            if (in_alarm_zone and not in_alarm_zone_prev):#calculate motion counts
                motion_count_upon_zone=motion_count
            if ((motion_count_upon_zone<motion_count) or (current_time_float>=(alarm_time_float+alarm_motion_wait))):#if motion or time passed
                alarm_begin=1
                if alarm_begin and not alarm_begin_prev:#First Alarm
                    alarm_start_time=time.time()
                    last_alarm_time=alarm_start_time
                    alarm_start_bool=1
                elif ((time.time()-last_alarm_time)>snooze_duration):#If time has passed
                    if not alarm_cancel:
                        last_alarm_time=time.time()
                        alarm_start_bool=1
                    elif ((time.time()-last_alarm_time)>61) and (motion_since_last_alarm<motion_count):#if cancel alarm
                        last_alarm_time=time.time()
                        alarm_start_bool=1
                    else:
                        alarm_start_bool=0
                else:
                    alarm_start_bool=0
            else:
                alarm_begin=0
        else:
            in_alarm_zone=0



        if ((time.time()-last_alarm_time)>60):#Check for motion 1 minute after alarm goes off
            if not counted_motion_bool:
                motion_since_last_alarm=motion_count
            counted_motion_bool=1
        else:
            counted_motion_bool=0



        if ((time.time()-print_time)>2):#Prints
            print("button: ",button_bool," Alarm_start: ",alarm_start_bool," Last alarm: ",last_alarm_time," Alarm zone: ",in_alarm_zone," alarm_begin: ",alarm_begin, " alarm cancel: ",alarm_cancel)
            print_time=time.time()



        if alarm_start_bool:#Snoozer Scheduler
            alarms_count+=1
        if alarms_count==2: 
            snooze_duration=300
            selected_alarm_name=alarm_names[1]
        elif alarms_count==3:
            snooze_duration=120
            alarm_cancel=True
            cancel_button=True
            selected_alarm_name=alarm_names[1]
        elif alarms_count==7:
            selected_alarm_name=alarm_names[1]

        if alarms_count>=3:
            alarm_cancel=True



        #Alarm Function
        alarm_active=alarm_f(alarm_duration,selected_alarm_name,button_bool,alarm_cancel,alarm_start_bool,last_alarm_time)
        turn_off_noise=False


        #Update Variables
        alarm_start_bool=0
        button_bool_prev=button_bool
        motion_bool_prev=motion_bool
        in_alarm_zone_prev=in_alarm_zone
        alarm_begin_prev=alarm_begin
        previous_day=t_s.day





    

def alarm_f(set_time, alarm_name, stop_bit, alarm_cancel,alarm_start_bool, last_alarm_time):
    global turn_off_noise
    global cancel_button
    if alarm_start_bool:#Start Alarm
        pygame.mixer.music.load(alarm_name)
        pygame.mixer.music.play(-1)

    if (last_alarm_time<(time.time()-set_time)):#Stop or Continue Alarm
        pygame.mixer.music.stop()
        return 0
    elif not alarm_cancel:
        if stop_bit and not cancel_button:
            pygame.mixer.music.stop()
            return 0
        else:
            return 1
    elif turn_off_noise:
        pygame.mixer.music.stop()
        turn_off_noise=False
        return 0
    else:
        return 1



if __name__ == "__main__":
    main()