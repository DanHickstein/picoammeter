'''
Script for logging data from a Keithley 6485 picoammeter. 
Probably works for the Keithley 6487 too. 

- Connect the picoammeter via the RS232 port. Works fine with an 
RS232 converter. 

- Go to the Device Manager and check which COM port the 
Keithley is connected to and change that in the code. 

- On the Keithley, press the COMM button and check that it is set
to RS232 mode.

- Maybe you will need to change the RS232 settings in the Keithley. 
To do this, press the CONFIG button, then press the COMM button. Ensure:
    Baud: 9600
    Flow: None
    TX Term: CR
    Parity: None
    Bits: 8
    
- If you get an "access denied" error connection to the correct
COM port, it is because that port is still in use. Try unplugging 
and re-plugging the USB-to-serial adaptor.
    
- Dan Hickstein (danhickstein@gmail.com) 2020-11-11

'''

import numpy as np
import matplotlib.pyplot as plt
import os
import time
import serial

##########################################
# change these parameters:
com_port = 3
sensitivity = .1
# This is the NPLC parameter, which sets the averaging time of the 
# picoammeter in "number of power line cycles"
# 0.1 = FAST
# 1 = MED
# 5 or 6 = SLOW
save_directory = 'timescans'
plots = True
current_multiplier = 1
# Set to -1 to change sign on the current.

###########################################

if not os.path.exists(save_directory):
    os.mkdir(save_directory)
print('Connecting to picoammeter...')

with serial.Serial('COM%i'%com_port, baudrate=9600, timeout=0.05) as kly:
    print('Initializing picoammeter')

    kly.write(b'*rst\r')
    kly.write(b'*IDN?\r')
    plt.pause(0.2)
    print("IDN: %s"%kly.readline().decode("UTF-8"))
        
    kly.write(b'SYST:ZCH ON\r')
    kly.write(b'INIT\r')
    kly.write(b'SYST:ZCOR OFF\r')
    kly.write(b'CURR:RANG:AUTO OFF\r')
    kly.write(b'CURR:RANG 2E-7\r')
    kly.write(b'CURR:NPLC %.1f\r'%sensitivity) #6 = high at 60 Hz
    kly.write(b'SYST:ZCH OFF\r')
    
    def request_data():
        kly.write(b'READ?\r')
        #kly.flushInput()

        while True:
            response = kly.readline()
            response = response.decode("UTF-8")
            print(response)
            if '\r' not in response:
                plt.pause(0.001)
            else:
                print(response)
                return response
                
    
    # set up some plots!
    plt.ion()
    plt.show(block=False)
    
    global exit_now
    keep_running = True
    
    def handle_close(evt):
        global keep_running
        keep_running = False
    
    fig, ax = plt.subplots(1,1, figsize=(10,6))
    fig.canvas.mpl_connect('close_event', handle_close)
    
    ax.set_ylabel('Current (amps)', fontsize=20)
    ax.set_xlabel('Time (sec)', fontsize=20)
    ax.grid(color='k', alpha=0.2)
    ax.grid(color='k', alpha=0.1, which='minor')
    
    l, = plt.plot(0,0, color='b', alpha=1.0)
    
    filenum = 1
    while True:
        if os.path.exists('timescans/%03i.txt'%filenum):
            filenum +=1
        else:
            break
    
    filename = 'timescans/%03i.txt'%filenum
    outfile = open(filename, 'w')
    outfile.write('Time(sec))\tAmps\n')
    
    amp_list = []
    times = []
    t0 = time.time()
    while keep_running:
        t = time.time() - t0
        t1 = time.time()
        
        data = request_data()
        print ('time to get data: %.3f sec'%(time.time()-t1))
        
        try:
            amps = float(data.split(',')[0][:-1])*current_multiplier
        except:
            print('Bad data: %s'%data)
            continue
    
        if np.abs(amps)>1:
            continue
    
        print('Time: %.3f sec, Current: %.3e amps'%(t, amps))
        outfile.write('%.5f\t%.5e\n'%(t, amps))
    
        if plots:
            times.append(t)
            amp_list.append(amps)
            l.set_data(times, amp_list)
    
            mean = np.mean(amp_list)
            rms_percent = np.sqrt(np.mean((amp_list-mean)**2))/mean * 100
            ax.set_title('%.4f nA, Mean: %.3e A, RMS: %.2f percent, filenum:%03i'%(amps*1e9, mean, rms_percent, filenum), 
                         fontsize=18, pad=15)
            ax.relim()
            ax.autoscale_view()
            fig.canvas.draw_idle()
            plt.pause(.001)
    
    outfile.close()
    plt.ioff()
    plt.show()
    
