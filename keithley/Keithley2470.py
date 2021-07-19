import pyvisa as visa
import numpy as np
import time
import atexit

class Keithley2470:
	def __init__(self, resource_str):
		self._resource_str = resource_str
		self._resource = visa.ResourceManager().open_resource(resource_str)
		
		self._is_writing = False
		self._is_reading = False
		
		self._idn = str(self._resource.query("*IDN?"))
		if 'KEITHLEY' not in self._idn or 'MODEL 2470' not in self._idn:
			raise RuntimeError(f'This instrument is not a Keithley 2470! You have connected to {self._idn} using the Keithley2470 class.')
		
		# Configure a safe shut down for when the class instance is destroyed:
		def _atexit():
			self.source_voltage = 0
			self.set_output('off')
		atexit.register(_atexit) # https://stackoverflow.com/a/41627098
		
		self.measure_voltage() # If this is not done, the instrument fails with a high probability. Don't ask me why.
		self.set_source_voltage(0)
		self.set_output('off')
	
	def write(self, msg:str):
		while self._is_writing:
			time.sleep(.1)
		self._is_writing = True
		self._resource.write(msg)
		self._is_writing = False
	
	def read(self):
		while self._is_reading:
			time.sleep(.1)
		self._is_reading = True
		answer = self._resource.read()
		self._is_reading = False
		return answer
		
	def query(self, msg):
		while self._is_writing or self._is_reading:
			time.sleep(.1)
		self._is_writing = True
		self._is_reading = True
		answer = self._resource.query(msg)
		self._is_writing = False
		self._is_reading = False
		return answer
	
	@property
	def idn(self):
		return self._idn
	
	def set_output(self, state: str):
		if state.upper() not in ['ON', 'OFF']:
			raise ValueError(f'The argument <state> must be "on" or "off", received {state} of type {type(state)}.')
		self.write(f':OUTPUT {state.upper()}')
	@property
	def output(self):
		answer = self.query(f':OUTPUT:STATE?')
		try:
			answer = int(answer)
		except:
			raise RuntimeError(f'Wrong answer received from the insturment. Was expecting either "0" or "1", received {answer}.')
		if answer == 0:
			return 'off'
		elif answer == 1:
			return 'on'
		else:
			raise RuntimeError(f'Wrong answer received from the insturment. Was expecting either "0" or "1", received {answer}.')
	@output.setter
	def output(self, state):
		self.set_output(state)
	
	def get_source_voltage(self):
		return float(self.query(':SOUR:VOLT?'))
	
	def set_source_voltage(self, volts: float):
		if isinstance(volts, float) or isinstance(volts, int):
			self._resource.write(f':SOURCE:VOLT:LEV {volts}')
		else:
			raise TypeError(f'The argument <voltage> must be a number (int or float), received {volts} of type {type(volts)}.')
	
	@property
	def source_voltage(self):
		return self.get_source_voltage()
	@source_voltage.setter
	def source_voltage(self, volts):
		self.set_source_voltage(volts)
	@property
	def voltage(self):
		raise AttributeError(f'Do not use "voltage", use "source_voltage".')
	@voltage.setter
	def voltage(self, _):
		raise AttributeError(f'Do not use "voltage", use "source_voltage".')
	
	def set_source_current_limit(self, amperes: float):
		if isinstance(amperes, float) or isinstance(amperes, int):
			self._resource.write(f':SOURCE:VOLT:ILIM {amperes}')
		else:
			raise TypeError(f'The argument <amperes> must be a number (int or float), received {amperes} of type {type(amperes)}.')
	
	def get_source_current_limit(self):
		return float(self.query(':SOUR:VOLT:ILIM?'))
	
	@property
	def current_limit(self):
		return self.get_source_current_limit()
	@current_limit.setter
	def current_limit(self, amperes):
		self.set_source_current_limit(amperes)
	@property
	def current(self):
		raise AttributeError(f'Do not use "current", use "current_limit".')
	@current.setter
	def current(self, _):
		raise AttributeError(f'Do not use "current", use "current_limit".')
	
	def beep(self, frequency=2222, time=500e-3):
		try:
			frequency = float(frequency)
			time = float(time)
		except:
			raise TypeError(f'Arguments <frequency> and <time> must be numbers. Received frequency={frequency} of type {type(frequency)} and time={time} of type {type(time)}.')
		if not 200 <= frequency <= 5000:
			raise ValueError(f'The argument <frequency> must be bounded between 200<=frequency<=5000.')
		if time > 1:
			raise ValueError(f'The argument <time> must be <= 1')
		self._resource.write(f':SYSTEM:BEEPER {frequency}, {time}')
	
	def measure_voltage(self):
		return float(self.query(':MEASURE:VOLT?'))
	
	def measure_current(self):
		return float(self.query(':MEASURE:CURRENT?'))

class Keithley2470SafeForLGADs(Keithley2470):
	# This class is basically the same as its parent class but it prevents 
	# to change the voltage abruptly, so the test structures are safe.
	def __init__(self, resource_str, polarity: str, slew_rate=10, volt_step=2.5):
		if not isinstance(polarity, str) or polarity not in ['positive','negative']:
			raise TypeError(f'<polarity> must be either "positive" or "negative"')
		self._polarity = 1 if polarity == 'positive' else -1
		self._slew_rate = slew_rate
		self._volt_step = volt_step
		
		super().__init__(resource_str=resource_str)
	
	@property
	def slew_rate(self):
		return self._slew_rate
	@property
	def volt_step(self):
		return self._volt_step
	
	def set_source_voltage(self, voltage):
		voltage = self._polarity*(voltage**2)**.5
		if self.output == 'off':
			super().set_source_voltage(voltage)
		else:
			while True:
				if ((voltage - self.get_source_voltage())**2)**.5 > self.volt_step:
					if voltage - self.get_source_voltage() >self. volt_step:
						super().set_source_voltage(self.get_source_voltage() + self.volt_step)
					else:
						super().set_source_voltage(self.get_source_voltage() - self.volt_step)
				else:
					super().set_source_voltage(voltage)
					break
				time.sleep(self.volt_step/self.slew_rate)
	
	def set_output(self, state: str):
		if state.lower() == 'off':
			if self.output == 'off':
				return
			else:
				self.set_source_voltage(0)
				super().set_output(state)
		else:
			if self.output == 'on':
				return
			else:
				setted_voltage = self.source_voltage
				super().set_source_voltage(0)
				super().set_output(state)
				self.source_voltage = setted_voltage

if __name__ == '__main__':
	import tkinter as tk
	import tkinter.messagebox
	import tkinter.font as tkFont
	import threading

	class Keithley2470SafeForLGADsGraphicControlSetVoltage(tk.Frame):
		def __init__(self, parent, keithley, *args, **kwargs):
			tk.Frame.__init__(self, parent, *args, **kwargs)
			self.parent = parent
			
			if not isinstance(keithley, Keithley2470SafeForLGADs):
				raise TypeError(f'The <keithley> must be an instance of Keithley2470SafeForLGADs, received an instance of {type(keithley)}.')
			self.keithley = keithley
			
			frame = tk.Frame(self)
			frame.grid()
			tk.Label(frame, text = f'Voltage ').grid()
			self.voltage_entry = tk.Entry(frame, font=tkFont.nametofont("TkDefaultFont"))
			self.voltage_entry.grid(row=0,column=1)
			
			def set_voltage():
				try:
					voltage = float(self.voltage_entry.get())
				except ValueError:
					tk.messagebox.showerror(message = f'Check your input. Voltage must be a float number, received "{self.voltage_entry.get()}".')
					return
				print('Please wait while the voltage is being changed...')
				self.keithley.source_voltage = voltage
				print('Voltage has been changed!')
			
			# ~ self.set_voltage_btn = tk.Button(self, text='Set this voltage', command=set_voltage)
			# ~ self.set_voltage_btn.grid()
			
			def enter(event=None):
				def thread_function():
					self.voltage_entry.config(state='disabled')
					set_voltage()
					self.voltage_entry.config(state='normal')
				threading.Thread(target=thread_function).start()
			self.voltage_entry.bind('<Return>', enter)
			self.voltage_entry.bind('<KP_Enter>', enter)

	class Keithley2470SafeForLGADsGraphicControlParametersDisplay(tk.Frame):
		def __init__(self, parent, keithley, *args, **kwargs):
			tk.Frame.__init__(self, parent, *args, **kwargs)
			self.parent = parent
			self._auto_update_interval = 1 # seconds
			
			if not isinstance(keithley, Keithley2470SafeForLGADs):
				raise TypeError(f'The <keithley> must be an instance of Keithley2470SafeForLGADs, received an instance of {type(keithley)}.')
			self.keithley = keithley
			
			frame = tk.Frame(self)
			frame.grid(pady=10)
			tk.Label(frame, text = 'Setted voltage: ').grid()
			self.setted_voltage_label = tk.Label(frame, text = '?')
			self.setted_voltage_label.grid()
			
			frame = tk.Frame(self)
			frame.grid(pady=10)
			tk.Label(frame, text = 'Measured voltage: ').grid()
			self.measured_voltage_label = tk.Label(frame, text = '?')
			self.measured_voltage_label.grid()
			
			frame = tk.Frame(self)
			frame.grid(pady=10)
			tk.Label(frame, text = 'Current compliance: ').grid()
			self.current_compliance_label = tk.Label(frame, text = '?')
			self.current_compliance_label.grid()
			
			frame = tk.Frame(self)
			frame.grid(pady=10)
			tk.Label(frame, text = 'Measured current: ').grid()
			self.measured_current_label = tk.Label(frame, text = '?')
			self.measured_current_label.grid()
			
			self.automatic_display_update('on')
			
		def update_display(self):
			self.setted_voltage_label.config(text=f'{self.keithley.source_voltage} V')
			self.measured_voltage_label.config(text=f'{self.keithley.measure_voltage():.5f} V')
			self.current_compliance_label.config(text=f'{self.keithley.current_limit*1e6} µA')
			self.measured_current_label.config(text=f'{self.keithley.measure_current()*1e6:.5f} µA')
		
		def automatic_display_update(self, status):
			if not isinstance(status, str):
				raise TypeError(f'<status> must be a string, received {status} of type {type(status)}.')
			if status.lower() not in ['on','off']:
				raise ValueError(f'<status> must be either "on" or "off", received {status}.')
			self._automatic_display_update_status = status
			
			def thread_function():
				while self._automatic_display_update_status == 'on':
					try:
						self.update_display()
					except:
						pass
					time.sleep(.6)
			
			self._automatic_display_update_thread = threading.Thread(target = thread_function)
			self._automatic_display_update_thread.start()
	
	root = tk.Tk()
	root.title('UZH Keythley safe control')
	default_font = tkFont.nametofont("TkDefaultFont")
	default_font.configure(size=16)
	keithley = Keithley2470SafeForLGADs('USB0::1510::9328::04481179::0::INSTR', polarity = 'negative')
	keithley.output = 'on'
	main_frame = tk.Frame(root)
	main_frame.grid(padx=20,pady=20)
	tk.Label(main_frame, text = 'UZH Keithley 2470 Safe Control', font=("Calibri",22)).grid()
	tk.Label(main_frame, text = f'Connected with {keithley.idn}', font=("Calibri",11)).grid()
	Keithley2470SafeForLGADsGraphicControlSetVoltage(main_frame, keithley).grid(pady=20)
	display = Keithley2470SafeForLGADsGraphicControlParametersDisplay(main_frame, keithley)
	display.grid(pady=20)
	
	def on_closing():
		display.automatic_display_update('off')
		print('PLEASE WAIT, the instrument is being shut down safely...')
		keithley.source_voltage = 0
		root.destroy()
	root.protocol("WM_DELETE_WINDOW", on_closing)

	root.mainloop()
