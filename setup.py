import setuptools

setuptools.setup(
	name = "keithley",
	version = "0",
	author = "Matias H. Senger",
	author_email = "m.senger@hotmail.com",
	description = "Control the Keythley power supply from Python",
	url = "https://github.com/keithley",
	packages = setuptools.find_packages(),
	classifiers = [
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
	],
	install_requires = [
		'pyvisa',
		'tkinter',
	],
)
