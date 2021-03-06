# run from /home/apdlab/larpixv2/larpix-socket-testing
# after running env3  
# cd ~/larpixv2/ ;  source bin/activate

import subprocess,sys
import larpix
from larpix import Controller
#from larpix.io.zmq_io import ZMQ_IO
from larpix.io import PACMAN_IO
from larpix.logger.h5_logger import HDF5Logger
import time
import tkinter as tk
from tkinter import ttk
import h5py
import pandas as pd

NumASICchannels = 64
DisabledChannels = [6,7,8,9,22,23,24,25,38,39,40,54,55,56,57]
TileChannelMask = [1] * NumASICchannels
for chan in DisabledChannels: TileChannelMask[chan]=0

TileChannelMask 

#[1, 1, 1, 1, 1, 1, 0, 0,
# 0, 0, 1, 1, 1, 1, 1, 1, 
# 1, 1, 1, 1, 1, 1, 0, 0, 
# 0, 0, 1, 1, 1, 1, 1, 1,
# 1, 1, 1, 1, 1, 1, 0, 0,
# 0, 1, 1, 1, 1, 1, 1, 1,
# 1, 1, 1, 1, 1, 1, 0, 0,
# 0, 0, 1, 1, 1, 1, 1, 1]

def init_controller():
	c = Controller()
	#c.io = ZMQ_IO('../configs/io/daq-srv1.json', miso_map={2:1})
	c.io = PACMAN_IO(config_filepath='/home/apdlab/larpixv2/configs/io/pacman.json')
	c.io.ping()
	return c

def init_board(c):
	#c.load('../configs/controller/pcb-3_chip_info.json')
	#c.load('../configs/controller/socket-board-v1.json')
	c.load('/home/apdlab/larpixv2/configs/controller/v2_socket_channel_1.json')
	c.io.ping()

def init_chips(c):
	#Set correct voltages
	c.io.set_vddd() # set default vddd (~1.8V)
	c.io.set_vdda() # set default vdda (~1.8V)
	# Disable Tile
	c.io.disable_tile()

	# Enable Tile 
	c.io.enable_tile()

	# First bring up the network using as few packets as possible
	c.io.group_packets_by_io_group = False # this throttles the data rate to avoid FIFO collisions
	for io_group, io_channels in c.network.items():
		for io_channel in io_channels:
			print("io_group,io_channel:",io_group,",",io_channel)
			#c.init_network(io_group, io_channel)
			c.init_network(io_group, io_channel,differential='True')

	# Configure the IO for a slower UART and differential signaling
	c.io.double_send_packets = True # double up packets to avoid 512 bug when configuring
	for io_group, io_channels in c.network.items():
		for io_channel in io_channels:
			chip_keys = c.get_network_keys(io_group,io_channel,root_first_traversal=False)
			for chip_key in chip_keys:
				c[chip_key].config.clk_ctrl = 1
				#c[chip_key].config.enable_miso_differential = [1,1,1,1]
				#c.write_configuration(chip_key, 'enable_miso_differential')
				c.write_configuration(chip_key, 'clk_ctrl')

	for io_group, io_channels in c.network.items():
		for io_channel in io_channels:
			c.io.set_uart_clock_ratio(io_channel, 4, io_group=io_group)

	c.io.double_send_packets = False
	c.io.group_packets_by_io_group = True

	chip_key
	for chip in c.chips.values(): print(chip.config)

	for chip in c.chips.values(): c.write_configuration(chip.chip_key)

	for chip in c.chips.values(): c.verify_configuration(chip.chip_key)

	chip = list(c.chips.values())[0] # selects 1st chip in chain
	#chip = list(c.chips.values())[1] # selects 2nd chip in chain
	#chip = list(c.chips.values())[2] # selects 3rd chip in chain
	#chip = list(c.chips.values())[3] # selects 3rd chip in chain
	print(chip)
	print(chip.chip_key)
	#print(chip.config)
	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)
	return chip

def enable_channel(chan):
	# Configure one channel to be on.
	chip.config.channel_mask = [1] * NumASICchannels  # Turn off all channels
	chip.config.channel_mask[chan]=0  # turn ON this channel
	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)

# Set global threshold
def setGlobalThresh(c,chip,Thresh=50):
	#print(chip.chip_key)	
	#print(id(chip.config))
	chip.config.threshold_global=Thresh
	c.write_configuration(chip.chip_key)
	#c.verify_configuration(chip.chip_key)

# Turn on a series of channels (a list would be better) on analog
# monitor and loop to the next one every 5 seconds.
def AnalogDisplayLoop(c,chip,firstChan=0,lastChan=NumASICchannels-1):
	for chan in range(firstChan,lastChan+1):
		AnalogDisplay(c,chip,chan)
		time.sleep(5)

# set a really long periodic reset (std=4096, this is 1M)
#chip.config.reset_cycles=1000000

# Turn on and display one channel on analog monitor
def AnalogDisplay(c,chip,chan):
	# Configure one channel to be on.
	chip.config.channel_mask = [1] * NumASICchannels  # Turn off all channels
	chip.config.channel_mask[chan]=0  # turn ON this channel
	# Enable analog monitor on one channel at a time
	c.enable_analog_monitor(chip.chip_key,chan)
	print("Running Analog mon on channel ",chan)
	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)
	#time.sleep(5) # move to the loop
	#c.disable_analog_monitor(chip.chip_key)

# Loop over approximately all channels and output analog mon for 5 seconds.
#AnalogDisplayLoop(0,NumASICchannels-1)

# Capture Data for channels in sequence

def ReadChannelLoop(c,chip,firstChan=0,lastChan=NumASICchannels-1,monitor=0):
	#sleeptime=0.1
	#c.start_listening()
	for chan in range(firstChan,lastChan+1):
		#print("Running chip ",chip," chan ",chan)
		if TileChannelMask[chan]!=0: 
			ReadChannel(c,chip,chan,monitor)
		#time.sleep(sleeptime)
	#c.stop_listening()
	chip.config.channel_mask = [1] * NumASICchannels  # Turn off all channels
	c.write_configuration(chip.chip_key)


def ReadChannel(c,chip,chan,monitor=0):
	# Configure one channel to be on.
	print("Running chip ",chip," chan ",chan)
	chip.config.channel_mask = [1] * NumASICchannels  # Turn off all channels
	chip.config.channel_mask[chan]=0  # turn ON this channel
	if monitor==1:
		# Enable analog monitor on channel
		c.enable_analog_monitor(chip.chip_key,chan)
		print("Running Analog mon for Pulser on channel ",chan)
	c.write_configuration(chip.chip_key)
	#c.verify_configuration(chip.chip_key)
	loop=0
	looplimit=1
	while loop<looplimit :
		# Read some Data (this also delays a bit)
		c.run(0.1,'test')
		#print(c.reads[-1])
		print("read ",len(c.reads[-1])," packets")
		loop=loop+1


def get_baseline_selftrigger(c,chip):
	# Capture Baseline for all channels one by one

	# Turn on periodic_reset
	chip.config.enable_periodic_reset = 1 
	# Reduce global threshold to get baseline data
	chip.config.threshold_global=5 
	# Extend the time for conversion as long as possible
	#chip.config.sample_cycles=150
	#chip.config.sample_cycles=1 #(set to default starting 2/21/2020)
	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)

	subprocess.run(["rm","testing.h5"])

	#logger declared and switched enabledc.
	c.logger = HDF5Logger("testing.h5", buffer_length=1000000)
	#c.logger = HDF5Logger("testing.h5", buffer_length=10000)
	c.logger.enable()
	c.logger.is_enabled()

	c.verify_configuration(chip.chip_key)
	print(chip.config)

	ReadChannelLoop(c,chip,0,NumASICchannels-1,0)

	print("the end")

	c.logger.disable()
	#c.logger.flush()
	#c.logger.close()

	import socket_baselines

def get_baseline_periodicselftrigger(c,chip):
	# Capture Baseline for all channels one by one

	# Turn on periodic_reset
	chip.config.enable_periodic_reset = 1 
	#chip.config.periodic_reset_cycles = 1000000 
	# Reduce global threshold to get baseline data
	chip.config.threshold_global=250 
	# Extend the time for conversion as long as possible
	#chip.config.sample_cycles=150
	#chip.config.sample_cycles=1 #(set to default starting 2/21/2020)
	# for v2 sample_cycles -> adc_hold_delay
	#chip.config.adc_hold_delay=150
	#chip.config.adc_hold_delay=1 #(set to default starting 2/21/2020)
	# enable periodic trigger
	chip.config.enable_periodic_trigger=1
	chip.config.periodic_trigger_mask= [0] * NumASICchannels
	chip.config.enable_hit_veto = 0
	# set trigger period (100ns*period_trigger_cycles)
	chip.config.periodic_trigger_cycles=1000 # 1k = 0.1ms
	#chip.config.periodic_trigger_cycles=10000 # 10k = 1ms
	#chip.config.periodic_trigger_cycles=20000 # 20k = 2ms
	#chip.config.periodic_trigger_cycles=100000 # 100k = 10ms
	#chip.config.periodic_trigger_cycles=1000000 # 1000k = 100ms
	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)

	subprocess.run(["rm","testing.h5"])

	#logger declared and switched enabledc.
	c.logger = HDF5Logger("testing.h5", buffer_length=1000000)
	#c.logger = HDF5Logger("testing.h5", buffer_length=10000)
	c.logger.enable()
	c.logger.is_enabled()

	c.verify_configuration(chip.chip_key)
	print(chip.config)
	print("Starting ReadChannelLoop...")

	ReadChannelLoop(c,chip,0,NumASICchannels-1,0)

	print("the end")

	c.logger.disable()
	#c.logger.flush()
	#c.logger.close()

	# turn off periodic trigger channels
	chip.config.periodic_trigger_mask= [1] * NumASICchannels
	chip.config.enable_periodic_trigger=0
	c.write_configuration(chip.chip_key)

	import socket_baselines


def get_baseline_periodicexttrigger(c,chip):
	# Capture Baseline for all channels

	# Turn on periodic_reset
	chip.config.enable_periodic_reset = 1 
	# Reduce global threshold to get baseline data
	chip.config.threshold_global=255 
	# Extend the time for conversion as long as possible
	#chip.config.sample_cycles=255
	# No more sample_cycles in v2?
	#chip.config.sample_cycles=1 #(set to default starting 2/21/2020)
	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)

	subprocess.run(["rm","testing2.h5"])

	chip.config.channel_mask = [0] * NumASICchannels  # Turn ON all channels
	chip.config.external_trigger_mask = [0] * NumASICchannels  # Turn ON all channels
	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)
	print(chip.config)

	#logger declared and switched enabledc.
	c.logger = HDF5Logger("testing2.h5", buffer_length=1000000)
	#c.logger = HDF5Logger("testing.h5", buffer_length=10000)
	c.logger.enable()
	c.logger.is_enabled()

	c.run(10,'test')
	print("read ",len(c.reads[-1]))
	print("the end")

	c.logger.disable()
	#c.logger.flush()
	#c.logger.close()

	import socket_baselines2


def PulseChannelLoop(firstChan=0,lastChan=NumASICchannels-1,amp=0,monitor=0):
	for chan in range(firstChan,lastChan+1):
		PulseChannel(chan,amp,monitor)

def PulseChannel(chan,amp=0,monitor=0):
        # Configure one channel to be on.
        chip.config.channel_mask = [1] * NumASICchannels  # Turn off all channels
        chip.config.channel_mask[chan]=0  # turn ON this channel
        if (monitor==1):
                # Enable analog monitor on channel
                c.enable_analog_monitor(chip.chip_key,chan)
                print("Running Analog mon for Pulser on channel ",chan)
        c.write_configuration(chip.chip_key)
        #c.verify_configuration(chip.chip_key)
        loop=0
        looplimit=5
        while loop<looplimit :
                c.enable_testpulse(chip.chip_key, [chan], start_dac=200)
                c.issue_testpulse(chip.chip_key, amp, min_dac=100)
                # Read some Data (this also delays a bit)
                #c.run(1,'test')
                print(c.reads[-1])
                loop=loop+1

def get_charge_injection():
	# Run some pulser 

	# Turn on periodic_reset
	chip.config.enable_periodic_reset = 1 
	# Reduce global threshold to get some data
	chip.config.global_threshold=50 
	# Extend the time for conversion as long as possible
	chip.config.sample_cycles=255
	chip.config.channel_mask = [1] * NumASICchannels  # Turn off all channels
	chip.config.external_trigger_mask = [1] * NumASICchannels  # Turn OFF ext trig all channels
	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)
	PulseChannelLoop(0,NumASICchannels-1,10,0)


def get_leakage_data():
	# This part is not quite ready yet.
	# Still not ready 20200212 - required thresh values depend on channel 
	# and you only want ot do it on channels that are good so far.

	# Turn off periodic_reset
	chip.config.enable_periodic_reset = 0 # turn off periodic reset
	chip.config.channel_mask = [1] * NumASICchannels  # Turn off all channels
	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)

	for thresh in [25,27,30,35]:
		setGlobalThresh(thresh)
		outfile = "testing" + str(thresh) + ".h5"
		print("Writing ",outfile)
		#logger declared and switched enabledc.
		c.logger = HDF5Logger(outfile, buffer_length=1000000)
		#c.logger = HDF5Logger("testing.h5", buffer_length=10000)
		c.logger.enable()
		c.logger.is_enabled()
		# Configure one channel to be on.
		for chan in range(NumASICchannels):	
			print("running channel ",chan)
			if socket_baselines.mean[chan] > 240 or socket_baselines.sdev[chan] < 2 : continue
			chip.config.channel_mask = [1] * NumASICchannels  # Turn off all channels
			chip.config.channel_mask[chan]=0  # turn ON this channel
			c.write_configuration(chip.chip_key)
			c.verify_configuration(chip.chip_key)
			# Read some Data (this also delays a bit)
			c.run(1,'test')
			print(c.reads[-1])
			print("the end")
		c.logger.disable()
		#c.logger.flush()
		c.logger.close()

def get_ThreshLevels(c,chip):


	#ChipSN = mychipIDBox[0].get()
	tempstatus = h5py.File("CurrentRun.tmp",mode='r')
	dset = tempstatus['CurrentRun']
	ChipSN = dset.attrs['ChipSN']
	tempstatus.close()

	#open hdf5 output file
	#ThreshDataFile = h5py("RateVsThreshData.h5",mode='a')
	RateThreshFrame = pd.DataFrame(columns = ['runtime','thresh','numsamples','dt','ChanName','Chan','ChipSN'])
	runtime=time.time()

	for chan in range(NumASICchannels):	
		if TileChannelMask[chan]==1: 
			print("running channel ",chan)
			chip.config.channel_mask = [1] * NumASICchannels  # Turn off all channels
			chip.config.channel_mask[chan]=0  # turn ON this channel
			c.write_configuration(chip.chip_key)
			c.verify_configuration(chip.chip_key)
			thresh=128
			step = 16
			rate = 0
			sampleTime = 0.30  # if you use smaller, need to use packet times for better precision
			stepthresh = 10
			while rate < 300 and ( thresh >= 1 and step >= 2 ) :
				setGlobalThresh(c,chip,thresh)
				# Read some Data (this also delays a bit)
				c.run(sampleTime,'test')
				#numsamples=len(c.reads[-1]['packet_type'==0])
				numsamples=len(c.reads[-1])
				print("Read ",numsamples," samples")
				# find duration of samples (first/last)
				sampleIter=0
				firstTime=0
				lastTime=0
				while sampleIter<numsamples :
					#if c.reads[-1].packets[sampleIter].chip_key != None :
					if c.reads[-1].packets[sampleIter].packet_type == 0 :
						#print(c.reads[-1].packets[sampleIter].packet_type)
						if c.reads[-1].packets[sampleIter].channel_id == chan :
							firstTime = c.reads[-1].packets[sampleIter].timestamp
							sampleIter=numsamples # To end the loop 
							#print("End time at ",numsamples-sampleIter-1)
					sampleIter=sampleIter+1
				sampleIter=0
				while sampleIter<numsamples :
					#if c.reads[-1].packets[sampleIter].packet_type == Packet_v2.DATA_PACKET :	
					#if c.reads[-1].packets[numsamples-sampleIter-1].chip_key != None :
					if c.reads[-1].packets[numsamples-sampleIter-1].packet_type == 0 :
						#print(c.reads[-1].packets[numsamples-sampleIter-1].packet_type)
						if c.reads[-1].packets[numsamples-sampleIter-1].channel_id == chan :
							lastTime = c.reads[-1].packets[numsamples-sampleIter-1].timestamp
							sampleIter=numsamples # to end the loop
							#print("End time at ",numsamples-sampleIter-1)
					sampleIter=sampleIter+1
				dt = lastTime-firstTime 
				if dt < 0 : dt =dt+2**24
				if dt == 0 : dt = dt+sampleTime*5E6
				dt = dt / 5E6
				#print(dt,"<- delta and first time: ",firstTime,"Last time: ",lastTime)
				#rate = numsamples/sampleTime			
				rate = numsamples/dt
				print("Channel ",chan," Thresh ",thresh," Rate ",rate)
				textchan = 'ch{:02d}'.format(chan)
				RateThreshFrame=RateThreshFrame.append({'runtime':runtime,'thresh':thresh,'numsamples':numsamples,
				'dt':dt,'ChanName':textchan,'Chan':chan,'ChipSN':ChipSN},ignore_index=True)
				print('len(RateThreshFrame.index)=',len(RateThreshFrame.index))
				thresh = thresh - step 
				if rate > stepthresh and step > 2 :
					thresh = thresh + step +step
					step = int(step/2)
					if step < 4 : sampleTime=1.0
					if rate < 100 :	stepthresh = stepthresh + stepthresh
			setGlobalThresh(c,chip,255)
			#print("c.reads is ",len(c.reads)," long")
			#print("c.reads is ",sys.getsizeof(c.reads)," long")
			c.reads.clear()
			#print("c.reads is ",len(c.reads)," long")
			#print("c.reads is ",sys.getsizeof(c.reads)," long")
			print("the end") # of chan loop


	#summaryFrame.to_csv("t.csv",mode='a',header=True)
	#RateThreshFrame.to_csv("RateThresh.csv",mode='a',header=False)
	RateThreshFrame.to_hdf("RateThresh.h5",mode='a',key='RateVsThreshV1')



def RunTests(c,chip):
	#Not sure how to find the mylabel object
	#window.mybutton.configure(text='Running...')
	#print(window.children)
	# this depends on order buttons are created, I think
	window.children['!frame'].children['!button'].configure(text='Running...')
	# grey out selection boxes
	for myiter in testCheckframe.children:
		# print('disabling ', myiter)
		testCheckframe.children[myiter].state(['disabled'])
		window.update()

	print("Running tests for Chip SN: ",mychipIDBox[0].get())
	ChipSN=mychipIDBox[0].get()

	tempstatus = h5py.File("CurrentRun.tmp",mode='w')
	dset = tempstatus.create_dataset("CurrentRun",dtype='i')
	dset.attrs['ChipSN']=ChipSN
	tempstatus.close()

	# Update progress boxes along the way
	#time.sleep(10)
	#find checkboxes that are enabled and run test
	testID=0
	for test in testList:
		#testFunctions.append(testFunctionNames[testID])
		#print(test)
		print(buttonVars[testID].get()," = ",testList[testID])
		if buttonVars[testID].get()=='0': 
			print("Skipping ",testList[testID])
		else :
			print("Running ",testList[testID])
			func = globals()[testFunctionNames[testID]](c,chip)
			#func(c,chip)
		#	text=test,variable=buttonVars[testID],command=printStatus))
		testID=testID+1

	#run test
	
	#report done

	# Reenable boxes
	#testCheckframe.state(['!disabled'])
	for myiter in testCheckframe.children:
		# print('disabling ', myiter)
		testCheckframe.children[myiter].state(['!disabled'])
		window.update()

	window.children['!frame'].children['!button'].configure(text='Run Test')


def trygui(c,chip):
	#window = tk.Tk()
	#global runPeriodicBaseline
	#global runBaseline
	mainframe = ttk.Frame(window, padding="3 3 12 12")
	mainframe.grid(column=0, row=0, sticky=("N, W, E, S"))
	window.columnconfigure(0, weight=1,uniform='a')
	window.rowconfigure(0, weight=1,uniform='a')
	window.title("ASIC Testing Controller")
	window.geometry('+100+100')
	#print("Window is at ",str(window))

	mylabel = ttk.Label(mainframe, text="ASIC testing")
	mylabel.grid(column=0,row=0)
	#print("mylabel is at ",str(mylabel))

	mybutton= ttk.Button(mainframe,text="Run Tests",command= lambda:RunTests(c,chip))
	#mybutton= ttk.Button(window,text="Run PeriodicBaseline")
	#print("mybutton is at ",str(mybutton))
	mybutton.grid(column=0,row=1)

	print("trygui")

	global mychipIDBox
	mychipIDBox = []
	def deploySN():
		#print('numChipVar = ',numChipVar)
		if int(numChipVar.get()) > len(mychipIDBox):
			for ChipNum in range(len(mychipIDBox)+1,int(numChipVar.get())+1):
				print(ChipNum)
				mychipIDBox.append(ttk.Entry(SNframe,width=6))
				mychipIDBox[ChipNum-1].grid(column=4,row=ChipNum,sticky='E') 
		if int(numChipVar.get()) < len(mychipIDBox):
			for ChipNum in range(len(mychipIDBox),int(numChipVar.get()),-1):
				print(ChipNum)
				mychipIDBox[ChipNum-1].state(['disabled'])
		for ChipNum in range(1,int(numChipVar.get())+1):
			mychipIDBox[ChipNum-1].state(['!disabled'])



#	print(runPeriodicBaseline.get()," = runPeriodicBaseline")
#	PerBaselineButton = ttk.Checkbutton(mainframe,text=
#		"Run PerBaseline",variable=runPeriodicBaseline,command=printStatus,onvalue="1",offvalue="0")
#	runPeriodicBaseline.set("1")
#	print(runPeriodicBaseline.get()," = runPeriodicBaseline")
#	runPeriodicBaseline.set("0")
#	print(runPeriodicBaseline.get()," = runPeriodicBaseline")
#	runPeriodicBaseline.set("1")
#	print(runPeriodicBaseline.get()," = runPeriodicBaseline")
#	#PerBaselineButton.state=runPeriodicBaseline
#	PerBaselineButton.grid(column=0,row=3,sticky="W")

#	print(runBaseline.get()," = runBaseline")
#	BaselineButton = ttk.Checkbutton(mainframe,text="Run Baseline",variable=runBaseline,command=printStatus)
#	#runBaseline=0
#	#BaselineButton.value=0 #runBaseline
#	BaselineButton.grid(column=0,row=4,sticky="W")

	global testList,testFunctionNames
	testList = ["Baseline Periodic SelfTrig",
			"Baseline Ext Trig",
			"Thresh Levels",
			"Leakage Data",
			"Charge Injection",
			"Pulse Data",
			"Analog Display"]
	testDefaults = [1,0,0,0,0,0,0]
	testFunctionNames = ["get_baseline_periodicselftrigger",
				"get_baseline_periodicexttrigger",
				"get_ThreshLevels",
				"get_leakage_data",
				"get_charge_injection",
				"PulseChannelLoop",
				"AnalogDisplayLoop"]
	testFunctions = [] 

	global buttonVars
	#buttonVars = [] #[len(testList)] # will hold StringVar()
	testButton = [] #[len(testList)] # will hold test checkbuttons

	testID=0
	#print(len(testList))
	global testCheckframe 
	testCheckframe = ttk.Frame(mainframe,padding="3 3 12 12")
	testCheckframe.grid(column=0,row=5)
	row=0	
	for test in testList:
		testFunctions.append(testFunctionNames[testID])
		#print(test)
		buttonVars.append(tk.StringVar())
		buttonVars[testID].set(testDefaults[testID])
		testButton.append(ttk.Checkbutton(testCheckframe,
			text=test,variable=buttonVars[testID],command=printStatus))
		testButton[testID].grid(column=0,row=row,sticky="W")
		row = row+1
		testID=testID+1

	#	print(runBaseline.get()," = runBaseline")
	#	BaselineButton = ttk.Checkbutton(mainframe,text="Run Baseline",variable=runBaseline,command=printStatus)
	#	BaselineButton.grid(column=0,row=5,sticky="W")

	textBox=tk.Text(mainframe, width = 40, height=10)
	textBox.grid(column=9,row=2,rowspan=10)

	closebutton= ttk.Button(mainframe,text="Quit",command=window.destroy)
	closebutton.grid(column=9,row=99,sticky='E')
	#print("closebutton is at ",str(closebutton))

	SNframe = ttk.Frame(mainframe, padding="3 3 12 12")
	SNframe.grid(column=9,row=0,rowspan=2,sticky='E')
	SNlabel = ttk.Label(SNframe, text="ASICs to test (1-10)")
	SNlabel.grid(column=1,row=0)
	numChipVar = tk.StringVar()
	#numChipVar.set("2")
	numChipWheel = tk.Spinbox(SNframe,from_=1,to=10,textvariable=numChipVar,command=deploySN)
	numChipWheel.grid(column=1,row=1,sticky='W')
	numChipVar.set("1")
	deploySN()
	#ChipSN = mychipIDBox[0].get()
	tempstatus = h5py.File("CurrentRun.tmp",mode='r')
	dset = tempstatus['CurrentRun']
	ChipSN = dset.attrs['ChipSN']
	tempstatus.close()
	if ChipSN:	mychipIDBox[0].insert(0,ChipSN)
	# seems that deploySN has to happen after first window paint
	# this makes it interactive?
	window.mainloop()
	

def mainish():

	#trygui()
	
	#exit()
	
	c=init_controller()
	init_board(c)
	chip=init_chips(c)	
	print(chip)	
	
	# Set global threshold
	setGlobalThresh(c,chip,100)

	# Read some Data
	#c.run(1,'test')
	#print(c.reads[-1])

	# Enable analog monitor on one channel
	c.enable_analog_monitor(chip.chip_key,28)
	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)

	# Turn on periodic_reset
	#chip.config.enable_periodic_reset = 1 # turn on periodic reset
	#c.write_configuration(chip.chip_key)
	#c.verify_configuration(chip.chip_key)

	# Turn off periodic_reset
	chip.config.enable_periodic_reset = 0 # turn off periodic reset
	# Turn on periodic_reset
	chip.config.enable_periodic_reset = 1 # turn off periodic reset

	# set a really long periodic reset (std=4096)
	#chip.config.periodic_reset_cycles=4096 # 819us
	#chip.config.periodic_reset_cycles=5096 # 1019us
	chip.config.periodic_reset_cycles=100000 # 20ms
	#chip.config.periodic_reset_cycles=1000000 # 200ms
	#chip.config.periodic_reset_cycles=10000000 # 2s

	#set ref vcm  (77 def = 0.54V)
	chip.config.vcm_dac=45
	#set ref vref  ( 219 def = 1.54V)
	chip.config.vref_dac=187
	#set ref current.  (11 for RT, 16 for cryo)
	#chip.config.ref_current_trim=16
	#set ibias_csa  (8 for default, range [0-15])
	#chip.config.ibias_csa=12

	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)

	# Disable analog monitor (any channel)
	c.disable_analog_monitor(chip.chip_key)
	c.write_configuration(chip.chip_key)
	c.verify_configuration(chip.chip_key)


	trygui(c,chip)

	#AnalogDisplayLoop(c,chip)
	#get_baseline_periodicexttrigger(c,chip) #ext trig not plugged in 8/20/2020
	#get_baseline_periodicselftrigger(c,chip)
	#get_ThreshLevels(c,chip)

def printStatus():
#	global runPeriodicBaseline
#	global runBaseline
	print("printStatus")
	#print(runPeriodicBaseline.get()," = runPeriodicBaseline")
	# runPeriodicBaseline.set("0")
	# print(runPeriodicBaseline.get()," = runPeriodicBaseline")
	#runPeriodicBaseline.set("1")
	#print(runPeriodicBaseline.get()," = runPeriodicBaseline")
	#print(runBaseline.get()," = runBaseline")
	myiter = 0
	for i in buttonVars:
		print(buttonVars[myiter].get()," = ",testList[myiter])
		myiter=myiter+1

# make the controlling window global. (will probably need a better name)
window = tk.Tk()
#runPeriodicBaseline = tk.StringVar()
#runBaseline = tk.StringVar()
#runPeriodicBaseline.set("1")
#runBaseline.set("0")

testList = []
buttonVars = []
testCheckfram = []

#runPeriodicBaseline="1"
#runBaseline="0"
mainish()

