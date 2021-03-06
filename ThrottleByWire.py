#J.Williams
#This script intends to move a stepper motor. It uses a RPi, a DRV8825 Stepper Motor Driver, a breadboard, a NEMA 17 Stepper Motor, a ADS1115 Analog to Digital Converter, and a power supply for now.
#A large portion of getting the stepper motor working correctly was achieved via watching a tutorial from 'rdagger68' on Youtube titled 'Raspberry Pi Stepper Motor Tutorial'.
#Another portion of getting the ADS1115 to work correctly was done by watching a tutorial from 'Ravivarman Rajendiran' on Youtube titled 'Analog Sensors Interfacing with Raspberry Pi using ADS1115 ADC. Step by step guide.'


#####DRV8825 Info
#DRV8825 Pin Layout (with pot screw in top left corner, pins facing down)
    ##ENABLE|VMOT#######
    ######M0|GND_MOT####
    ######M1|B2#########
    ######M2|B1#########
    ###RESET|A1#########
    ###SLEEP|A2#########
    ####STEP|FAULT######
    #####DIR|GND_LOGIC##

#DRV8825 Pin Assignment
    #Enable> Not Used
    #M0> (Optional) Pi GPIO 14 (Physical Pin 8)    (Without, operates in Full Step mode)
    #M1> (Optional) Pi GPIO 15 (Physical Pin 10)    (Without, operates in Full Step mode)
    #M2> (Optional) Pi GPIO 18 (Physical Pin 12)    (Without, operates in Full Step mode)
    #RESET> Pi 3.3V+ (Supposedly DRV8825 will not operate if this is not pulled to HIGH position)
    #SLEEP> Pi GPIO 17 (Physical Pin 11) (Could also be placed on 3.3V+ pin, but would always leave stepper motor engaged, which may result in unnecessary power draw)
    #STEP> Pi GPIO 21 (Physical Pin 40) (IIRC when pulsed, tells motor to take one step)
    #DIR> Pi GPIO20 (Physical Pin 38)
    #VMOT> Power Supply 12V+ (Be careful connecting anything over 3.3V as this may damage the Pi) (Also note that a 100 uF capacitor was used across the VMOT/GND_MOT pins in case of voltage spike issues)
    #GND_MOT> Power Supply 12V- (also connect to GND LOGIC Pin just in case the other ground circuit is bad)
    #B2> Motor Pole (Pair with B1) (Do not connect until DRV8825 Pot is adjusted)
    #B1> Motor Pole (Pair with B2) (Do not connect until DRV8825 Pot is adjusted)
    #A1> Motor Pole (Pair with A2) (Do not connect until DRV8825 Pot is adjusted)
    #A2> Motor Pole (Pair with A1) (Do not connect until DRV8825 Pot is adjusted)
    #FAULT> Not Used
    #GND_LOGIC> Pi GND (Physical Pin 39) (also connect to GND_MOT Pin just incase other ground circuit is bad)
#####


#####Description of how this was connected. This may be redundant information.
    #DRV8825 Logic_GND and Motor_GND pins tied to GND of breadboard. Logic GND and Motor GND were tied together at the GND on the breadboard, just to ensure a common ground.
    #Motor Ground tied to the power supply ground (negative terminal)
    #VMOT tied to the power supply (+ terminal)(Do NOT connect the power supply (+) to anything but the VMOT pin on the DRV8825, as this will be using more voltage than the Pi can handle and will damage it.)
    #100 uF capacitor used across the VMOT and GND pins for the DRV8825. This is done to have a capacitor in parallel so that any voltage spikes will be 'absorbed' by the capacitor.
    #SLEEP pin on the DRV8825 is connected to GPIO pin 17 on Pi. (Can connect this to 3.3V (+) pin if do not need to put the motor to sleep when not turning (pedal not pressed) if want to save power.)
    #RESET Pin of DRV8825 to 3.3V (+)
    #STEP Pin to GPIO 21 of Pi
    #DIR Pin to GPIO 20 of Pi
    #3.3V RPi Pin (Physical Pin 1) to 3.3V (+) Pin on breadboard
    #RPi GND Pin (Physical Pin 6) to 3.3V (-) Pin on breadboard
    #Before connected motor, turn power supply on and set to 12V, then measure voltage on the Pot Screw on the DRV8825 and turn screw clockwise to reduce voltage (or ccw to increase) until around 0.5V, or whatever voltage is required.
    #For the DRV8825, approximate current limit in amps is twice the volts at the pot screw.
    #The DRV8825 steps the voltage down, so do not use power supply current as is for estimating motor current.
    #Once the voltage is regulated properly, ensure power supply is off and connect one pole pair of motor to A1 and A2, and the other to B1/B2 of DRV8825. If unsure which are paired, place an LED across leads with no power connected and turn motor by hand. If lights up, they are paired.
    #
    #The M0,M1,and M2 pins on the DRV8825 are used to change the stepping mode. With the default of these pins being low, full step is used. However, can have microstepping if using the pins.
    #
    #The HPC pedal setup was done by connecting wires to the Delphi 6 pin connector, filling the A, B, and C terminals.
    #Believe this is a Mouser PN 829-12162261 connector
    #Pin A(F) is signal out, pin B(E) is ground, and pin C(D) is 5V in.
    #
    #The axle input shaft speed sensor was setup using pin 1 as power in, pin 2 as output signal, and pin 4 as ground.
#####
    
#####ADS1115 Pin Layout ---(and Placement)
    #VDD----Positive Voltage In (3.3 V from RPi)
    #GND----Ground
    #SCL----To SCL1 Pin (physical pin 5) on RPi
    #SDA----To SDA1 Pin (physical pin 7) on RPi
    #ADDR---(Not used)
    #ALRT---(Not used)
    #A0-----Signal Channel 0 (Pedal Position Sensor)
    #A1-----Signal Channel 1 (Axle Input Shaft Speed Sensor)
    #A2-----Signal Channel 2 (Throttle Position Sensor)
    #A3-----(Not Used)
#####
    


#####Library Imports
import time
from time import sleep
import RPi.GPIO as GPIO
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio
import math
import numpy as np
#####



#####ADS1115 channel voltage input code (use 'channel_name.voltage' to get voltage):
#Create the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)
#Create the ADC object using the I2C bus
ads = ADS.ADS1115(i2c)
ads.gain = 1 #GAIN
#Create single ended input on channel 0 (A0)
pps = AnalogIn(ads, ADS.P0) #Pedal Position Sensor
axle_spd_sens = AnalogIn(ads, ADS.P1) #Axle Shaft Speed Sensor
tps = AnalogIn(ads, ADS.P2) #Throttle Position Sensor
pedalswitch = AnalogIn(ads, ADS.P3) #Pedal Switch
#Note: To install the package necessary for using the ads module, try 'sudo pip3 install adafruit-circuitpython-ads1x15'
#####



#####Setup

#Motor Info
#NEMA17 Stepper Motor (PN: 17HS19-2004S1)
Step_deg = 1.8 #degrees for each step

#Setting up Microstepping dictionary 
#Microstepping Resolution Setup for DRV8825 [From DRV8825 datasheet]
#This will later be used to allow motor to more finely tune vs move quickly, depending on speed conditions. See step_mode() function.
RESOLUTION = {'Full': (0,0,0),
             'Half': (1,0,0),
             '1/4':  (0,1,0),
             '1/8':  (1,1,0),
             '1/16': (0,0,1),
             '1/32': (1,0,1),
             '1/64': (1,1,1)}


#Setup for RPi pin being high/low depending on motor direction desired
CW = 0 #Clockwise rotation
CCW = 1 #Counterclockwise rotation

#RPi Pin Assignments 
DIR = 20 #Direction --- GPIO Pin Label
STEP = 21 #Step --- GPIO Pin Label
MODE = (14,15,18) #Microstep Resolution Mode --GPIO Labels for M0, M1, and M2.
SLEEP = 17 #Sleep --- GPIO Pin Label

#GPIO Setup
GPIO.setmode(GPIO.BCM) #Set Pins to use the GPIO labels/broadcom labeling system instead of physical pin assignment
GPIO.setup(DIR, GPIO.OUT) #Direction Pin on Pi is set to an output pin
GPIO.setup(STEP, GPIO.OUT) #Step Pin on Pi is set to an output pin
GPIO.setup(MODE, GPIO.OUT) #Set mode pin on Pi as an output.
GPIO.setup(SLEEP, GPIO.OUT) #Set sleep pin on Pi as an output pin.
GPIO.output(DIR, CW) #Direction set to CW initially (Rpi pulls DIR pin high?) 
GPIO.output(SLEEP, 1) #enable stepper motor
#####



###Program###
#Program will be written to move stepper motor forward (open throttle) if throttle is not already opened max
#also only if the desired speed is higher than actual speed, and also only if acceleration rate is not too high.

#Functions
def ax_spd_sens_v_to_veh_spd(): #convert axle speed sensor voltage to vehicle speed in mph
    decimal_places = 2 #used at end to round returned value
    rounding_integer = 5 #used at end to round returned value
    #n_teeth = 32 #number of teeth per revolution of axle input shaft 
    axle_speed_sensor_v_in = 3.3 #Sensor Supply Voltage
    axle_spd_sens_volt_per_rpm = axle_speed_sensor_v_in/5500 #volts per 5500 rpm (25mph with 18" tires)
    axle_input_rpm = axle_spd_sens.voltage/axle_spd_sens_volt_per_rpm #This line takes the input from the speed sensor
    axle_ratio = 11.47
    tire_dia = 18 #inch
    f_roll_rad = 0.965 #rolling radius factor
    tire_circ = tire_dia*math.pi*f_roll_rad 
    tire_rpm = (axle_input_rpm)/axle_ratio
    veh_spd_inchpermin = tire_rpm*tire_circ
    veh_spd = veh_spd_inchpermin*((60/1)*(1/12)*(1/5280))
    if veh_spd < 0:
        veh_spd = 0
    return np.around(veh_spd/rounding_integer, decimal_places)*rounding_integer #round according to first two values in function
    
def pps_v_to_des_spd(): #convert pedal position sensor voltage to desired speed, in mph
    decimal_places = 2 #used at end to round returned value
    rounding_integer = 5 #used at end to round returned value
    pps_v_in = 3.3 #3.3 or 5 (ECU delivers 5V)
    pps_mode = "potentiometer" #"potentiometer" or "pedal"
    if pps_mode == "potentiometer":
        pps_v_min = 0
        if pps_v_in == 3.3:
            pps_v_max = 3.3
        elif pps_v_in == 5:
            pps_v_max = 5
    elif pps_mode == "pedal":
        if pps_v_in == 3.3:
            pps_v_min = 0.724 #measured value with HPC
            pps_v_max = 2.81 #measured value with HPC
        elif pps_v_in == 5:
            pps_v_min = 1.15 #measured value with HPC
            pps_v_max = 3.876 #measured value with HPC
    else:
        print ("Error with pps_v_to_des_spd function")
    #This next section creates a non-linear map for pedal position vs speed desired
    pps_percent = (pps.voltage - pps_v_min) / (pps_v_max - pps_v_min) * 100
    pedalspeedmap_pedalpos=np.arange(0,101,5) #create an array from 0 to 100
    #pedalspeedmap_speed=[0,.25,.6,1,1.5,2.1,2.7,3.35,4,4.65,5.4,6.1,6.9,7.7,8.5,9.3,10.1,10.8,11.4,11.8,12]
    pedalspeedmap_speed_percentage=[0,0.02,0.05,0.085,0.125,0.175,0.225,0.28,0.333,0.3875,0.45,0.51,0.575,0.64,0.71,0.775,0.84,0.9,0.95,0.98,1]
    pedalspeedmap_speed = np.multiply(pedalspeedmap_speed_percentage, cruise_spd)
    des_spd = np.interp(pps_percent, pedalspeedmap_pedalpos, pedalspeedmap_speed) #linear interpolation of speed map
#   #The below method uses a curve fit instead of linear interpolation
#     x=pedalspeedmap_pedalpos
#     y=pedalspeedmap_speed
#     curve=np.polyfit(x,y,3)
#     poly = np.poly1d(curve)
#     des_spd = poly(pps_percent)
#
    if des_spd < 0:
        des_spd = 0
    else:
        des_spd = np.around(des_spd/rounding_integer, decimal_places)*rounding_integer #round according to first two values in function
    #
    return des_spd

def tps_v_to_deg_throttle(): #convert throttle position sensor voltage to deg of opening
    tps_voltage = tps.voltage #Storing TPS voltage as variable so that everything is evalauted from same value within this function
    tps_v_in = 5 #volts --- Input either 3.3 or 5. On Vehicle, ECU delivers 5 V
    deg_throttle_min = 0
    deg_throttle_max = 80 #may be 82, see variation here from throttle body to throttle body
    if tps_v_in == 3.3: #3.3V Input to Throttle Body
        tps_v_min = 0.41 #Fully Closed throttle signal reading
        tps_v_max = 2.53 #Fully Open Throttle signal reading
    elif tps_v_in == 5: #5V Input to Throttle Body
        tps_v_min = 0.652 #Fully Closed throttle signal reading 
        tps_v_max = 3.865 #Fully Open Throttle signal reading
    else:
        print("Error with tps_v_to_deg_throttle function")
    #
    if tps_voltage < tps_v_min: #in case tps signal is slightly lower from throttle body, round to tps_v_min for now
        tps_voltage = tps_v_min
    elif tps_voltage > tps_v_max: #in case tps signal is slightly higher from throttle body to throttle body, round to tps_v_max value for now
        tps_voltage = tps_v_max
    #
    deg_throttle = 0+(tps_voltage-tps_v_min)*(deg_throttle_max-deg_throttle_min)/(tps_v_max-tps_v_min) #linear interpolation
    if deg_throttle == -0: #was seeing negative zero sometimes, did not want to see negative zero. did not want to use abs() in case it goes below negative zero I would want to see it in testing.
        deg_throttle = 0
    #
    return deg_throttle

def spd_error(): #calculates the difference between desired speed and actual speed
    diff = des_spd - act_spd #Positive Value indicates user commanding to go faster
    return diff

def step_mode(): #Allows the motor driver to control microstepping, depending upon how close actual and desired speeds are, in order for throttle control to be more precise vs quick
    diff = abs(spd_error())
    if diff < 1:
        step_mode = '1/64'
    elif diff < 2.5:
        step_mode = '1/32'
    elif diff < 3:
        step_mode = '1/16'
    elif diff < 3.5:
        step_mode = '1/8'
    elif diff < 4:
        step_mode = '1/4'
    elif diff < 5:
        step_mode = 'Half'
    else:
        step_mode = 'Full'
    return step_mode

def step_mode_pedal_up(): #function to control speed at which throttle closes when pedal up/throttle open loop is active
    tps_deg = tps_v_to_deg_throttle()
    diff = tps_deg - tps_deg_max_pedal_up
    if diff < 0.1:
        step_mode = '1/64'
    elif diff < 0.25:
        step_mode = '1/32'
    elif diff < 0.5:
        step_mode = '1/16'
    elif diff < 1:
        step_mode = '1/8'
    elif diff < 3:
        step_mode = '1/4'
    elif diff < 5:
        step_mode = 'Half'
    else:
        step_mode = 'Full'
    return step_mode  

def delay(arg = None): #Controls the delay between steps of stepper motor (optional 'pedal_up' argument)
    delay_FullStep = 0.00125 #Time to dealay between each step, if full stepping
    if arg == None: #Assign STEP_MODE to variable so it does not iterate through function each time below
        STEP_MODE = step_mode()
    elif arg == 'pedal_up':
        STEP_MODE = step_mode_pedal_up()
    else:
        print("delay function error, enter no arguments, or enter 'pedal_up' as argument")
    if STEP_MODE == 'Full':
        delay = delay_FullStep
    elif STEP_MODE == 'Half':
        delay = delay_FullStep/2
    elif STEP_MODE == '1/4':
        delay = delay_FullStep/4
    elif STEP_MODE == '1/8':
        delay = delay_FullStep/8
    elif STEP_MODE == '1/16':
        delay = delay_FullStep/16
    elif STEP_MODE == '1/32':
        delay = delay_FullStep/32
    elif STEP_MODE == '1/64':
        delay = delay_FullStep/64
    if delay < 0.000002:
        delay = 0.000002 #min delay of 2 microseconds
    return delay

def pedalswitchstate(): #returns the pedal switch state (Pedal Up = 0 ; Pedal Down = 1)
    if pedalswitch.voltage > 1.5: #Check voltage from pedal switch
        psw = 1
    else:
        psw = 0
    return psw
    
def step_open(): #moves the stepper motor 'forward' one step
    GPIO.output(DIR, CW)
    GPIO.output(STEP, GPIO.HIGH)
    GPIO.output(STEP, GPIO.LOW)
    sleep(delay())

def step_close(): #moves the stepper motor 'backward' one step
    GPIO.output(DIR, CCW)
    GPIO.output(STEP, GPIO.HIGH)
    GPIO.output(STEP, GPIO.LOW)
    sleep(delay())

#End of functions





#enter a forever while loop, until 'CTRL+c' keyboard interrupt occurs, then cleanup GPIO pins
try:   
    print("Program Begun ; Press 'CNRL+c' to stop program and cleanup GPIO Pins")
    
    #variables
    cruise_spd = 12 #desired cruising speed in mph
    accel_rate_cap = 2.5 #mph/s --- This is the maximum acceleration rate desired. If going beyond this, throttle should be limited
    tps_deg_max_pedal_up = 0.5 #maximum amount of degrees the throttle can have when pedal is up. This may not be needed if TRS is strong enough, but stepper motor is not strong enough to guarantee to hold against TRS all the time unfortunately
    #psw_loop_allow = True #defining before while loop, used to cancel out of a loop where pedal switch is up and tps value is not changing after so many iterations of stepping the motor
    step_stop = False
    tps_deg_stop_min = 0.2 #degrees of tps. This is used later to say if below this value, assume TPS is closed, because the TRS may not always be able to close completely due to unwinding to allow stepper motor to function.
    tps_deg_stop_max = 78 #degrees of tps. This is used later to say if above this value ,assume TPS is opened fully, because of tolerances of sensors etc. do not want to attempt to keep opening already fully open throttle
    
    #variables needed for printing and accel rate calculations
    accel_rate = 0 # setting initial acceleration rate, in mph/s, set to 0 until enough data to change
    itr = 0 #counter of iterations of while loop below, setting to 0 initially
    print_itr_reset_count = 25 #number of iterations before iterations reset for print loop, controls how often values print to screen, if that section of code not commented out
    mov_avg_itr_window = 25 #controls how many iterations are used for the moving average calculations
    veh_spd_list = [] #creates an empty list of vehicle speeds, to be used later to find average accel rate
    time_list = [] #creates an empty list of times, to be used later for caclulating accel rates
    step_history = [] #creates an empty list of what the stepper motor steps have been, to be used later for making sure later if lots of steps occur, throttle actually moves
    step_history_max_count = 50
    tps_history = [] #creates an empty list of what the tps value has been, to be used later for making sure later if lots of steps occur, throttle actually moves
    
    sleep(0.1) #wait some time to be sure sleep pin is activated
    
    while True:
        #get the current values of the sensors, and convert to useful numbers
        act_spd = ax_spd_sens_v_to_veh_spd()#gets voltage reading from axle input shaft speed sensor and converts to vehicle speed in mph
        des_spd = pps_v_to_des_spd() #Converts voltage reading to desired vehicle speed in mph
        tps_deg = tps_v_to_deg_throttle() #throttle opening in degrees, used to determine if throttle already at max/min limits before moving stepper motor further             
        psw = pedalswitchstate() #pedal switch position (Pedal Up = 0; Pedal Down = 1)
        
        #Setup microstepping mode
        GPIO.output(MODE, RESOLUTION[step_mode()]) #Sets full/microstepping up. See 'RESOLUTION' dictionary. This is used in order to change the speed at which the throttle will move, so that near cruising speeds it can be more fine tuned, etc.
        
        #Calculate acceleration rate (the time period is controlled by the iterations 'mov_avg_itr_window' size now, but can change to wait for difference to be over some value...
        veh_spd_list.append(act_spd)  #add current vehicle speed to vehicle speed list
        time_list.append(time.perf_counter()) #add current time to time list
        #the following if statement can probably be removed once program seems finalized
        if len(veh_spd_list) != len(time_list): #warn if lists are not equal length
             print("vehicle speed list length does not match time list length")
             break
        if des_spd > 1 and psw == 0: #checks for non-agreeing pedal switch/sensor values. Not set to zero because of sensor/switch/pedal tolerances.
            print("Pedal switch open but desired speed not near zero")
        if len(veh_spd_list) >= mov_avg_itr_window:  #allow list length to build before removing old data
            veh_spd_list = veh_spd_list[1:] #remove the oldest speed in list
            time_list = time_list[1:] #remove the oldest time in list        
            accel_rate = (veh_spd_list[-1]-veh_spd_list[0])/(time_list[-1]-time_list[0]) #calculate accel rate from oldest and newest speed and time values in lists
            # confirmed accel rate calculated correctly, but need to look into the time delta of this.
            # may want to have statement to only calculate if time difference is a certain delta or greater? perhaps 5 Hz?      
        
        
        
        #This section for moving stepper motor --- steps motor forward or backward by 1 step (or does nothing if delta beteen des_deg & act_deg are less than the degrees per step, as to eliminate cycling back and forth 1 step constantly)
        if des_spd > act_spd and tps_deg < tps_deg_stop_max and accel_rate < accel_rate_cap and psw == 1:  #want to go faster, not hitting max throttle or accel rate cap
            step_open()
            step_history.append(1)  #1 indicates movement forward
            tps_history.append(round(tps_deg,1))
        elif des_spd > act_spd and tps_deg > tps_deg_stop_min and accel_rate > accel_rate_cap and psw == 1: #want to go faster, but hitting acccel rate cap
            step_close()
            step_history.append(-1) #-1 indicates movement backwards
            tps_history.append(round(tps_deg,1))
        elif des_spd < act_spd and tps_deg > tps_deg_stop_min and psw == 1: #vehicle going faster than desired, close throttle
            step_close()
            step_history.append(-1) #-1 indicates movement backwards
            tps_history.append(round(tps_deg,1))
        elif psw == 0 and tps_deg > tps_deg_stop_min: #if pedal switch is open, close throttle
            GPIO.output(MODE, RESOLUTION['Full']) #changes the stepping mode to full to close the throttle as quickly as possible, as there may be an issue.
            step_close()
            step_history.append(-1)#-1 indicates movement backwards
            tps_history.append(round(tps_deg,1))
        else: #do not move throttle, but need to update step history list etc.
            step_history.append(0) #0 indicates no movement
            tps_history.append(round(tps_deg,1))
            #now we have a list of the movements of the stepper motor over a recent short amount of time
        
        if len(step_history) >= step_history_max_count: #make sure step history list does not get too long
            step_history = step_history[1:]
            tps_history = tps_history[1:]
            if tps_history.count(tps_history[0]) >= len(tps_history):
                tps_history_same = True
            else:
                tps_history_same = False
            if step_history.count(step_history[0]) >= len(step_history): #if the first element in step history list exist for all of the elements (length of) the list
                step_history_same = True
#Have not been able to get the step_stop to operate correctly for some reason...need to see if can fix or find alternate method              
             
            


        
#         #Loop to check if pedal is up, and then close throttle if not already closed
# #The following section I have not been able to figure out yet. I want only x iterations to occur, but not to jump back into the loop after it has been broken, unless the throttle has went past a certain degree since then
#        psw_loop_cancel = False #used to make sure not cycling in/out of below while loop continually
#        psw_loop_itr = 0 #Sets iteration counter for below loop
#        psw_loop_itr_max = 10 #set max number of steps allowed by stepper motor for below loop, to prevent a condition where perhaps the tps value is not right so the throttle cable gets wrapped around the stepper motor pulley backwards
#        if tps_deg > 5:
#            psw_loop_allow = True
#        while (psw == 0) and (tps_deg > tps_deg_max_pedal_up) and (psw_loop_allow == True): #if the pedal switch is open, and throttle is still open, close throttle (did not make 0 in case reading is not exactly 0 when at throttle stop)
#            if psw_loop_itr >= psw_loop_itr_max:
#                psw_loop_allow = False
#            GPIO.output(MODE, RESOLUTION[step_mode_pedal_up()]) #changes the stepping mode according to the step_mode_pedal_up function
#            GPIO.output(DIR, CCW)
#            GPIO.output(STEP, GPIO.HIGH)
#            GPIO.output(STEP, GPIO.LOW)
#            sleep(delay('pedal_up'))
#            psw_loop_itr += 1 #add iteration to psw loop iteration counter
#            tps_deg = tps_v_to_deg_throttle()
#            print('itr is',psw_loop_itr)
#            if tps_deg <= tps_deg_max_pedal_up: # this loop used to make sure the throttle position sensor voltage bouncing around does not cause it to go in/out of the while loop
#                #do two extra steps, to make less likely to approach tps limit when tps value bounces around
#                GPIO.output(STEP, GPIO.HIGH) 
#                GPIO.output(STEP, GPIO.LOW)
#                sleep(delay('pedal_up'))
#                GPIO.output(STEP, GPIO.HIGH) 
#                GPIO.output(STEP, GPIO.LOW)
#                sleep(delay('pedal_up'))
#                psw_loop_cancel = True
#            print("newloop, tps is: ",tps_deg," psw state is:",psw, "delay is:",delay('pedal_up'))
           
                
                                   
        
#         #This next portion for testing only
#         print("speeds:",veh_spd_list[0:4],"...",veh_spd_list[-4:])
#         print("time:",time_list[0:4],"...",time_list[-4:])
#         print("accel_rate:",accel_rate)
#         print("")
#         if len(time_list) > 5:
#                print("time_delta:",(time_list[-1]-time_list[-2]))
             
        itr += 1 #add 1 to while loop iteration counter    
    
        #this next if statement/section for testing program only
        #may need to change above itr line or reset if removing this section
        if itr >= print_itr_reset_count: #print desired and actual throttle position once every 75 iterations (to make easier to read) (modulo)
            print("tps_deg:",round(tps_deg,2),"deg  ","act_spd:",round(act_spd,2)," Des_veh_spd:",round(des_spd,2),"  accel_rate:",round(accel_rate,2)," mph/s","  step mode is: ",step_mode(),"min delay is:",round(delay(),7),"  psw is: ",psw)
            #print(step_history)
            itr = 0 #reset iterations
            

except KeyboardInterrupt:
    GPIO.output(SLEEP, GPIO.LOW) #disable stepper motor (to keep from getting hot unneccesarily)
    GPIO.cleanup() #reset GPIO pins to inputs to protect against shorting accidentally
    print("Program Ended; GPIO pins cleaned up")

#General Comments on things to do:
#May want to look into accel rate time and make a minimum time delta before it overrides the accel rate calc? Since RPi time does not seem consistent...
#Note, have found the stepper motor loses position when changing microstepping, or when getting close to full throtle,...with TRS unwound slightly, seems to behave fine but may cause throttle not to close completely sometimes
#Also found that when achieving max accel rate, stepper sometimes loses position
#May want to see about adding feature to only attempt to close throttle if last x iterations have 1) been below say 2 degrees, and 2) have not resulted in a noticeable tps value decrease
#Perhaps the above would be a good reason to use/learn OOP and use a class that can count the number of times it has been used?



