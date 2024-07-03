new_boot = '''
import storage
storage.remount('/', %s)
'''

def to_usb():
	answer = input("This will replace boot.py in the current directory to give write permissions to USB/computer. Continue? (y/n) ")
	if answer.strip().lower() == 'y':
		try:
			with open('boot.py', 'w') as f:
				f.write(new_boot % ("True"))
		except OSError:
			print("USB/computer already has write permissions")
		else:
			print("Operation completed")
	else:
		print("Operation canceled")

def to_cpy():
	answer = input("This will replace boot.py in the current directory to give write permissions to CircuitPython. Continue? (y/n) ")
	if answer.strip().lower() == 'y':
		try:
			with open('boot.py', 'w') as f:
				f.write(new_boot % ("False"))
		except OSError:
			print("CircuitPython already has write permissions")
		else:
			print("Operation completed")
	else:
		print("Operation canceled")

def main():
	answer = input("Give write permissions to USB/computer (0) or CircuitPython (1)? ")
	assert answer == '0' or answer == '1'
	if answer == '0':
		to_usb()
	else:
		to_cpy()

if __name__ == "__main__":
	main()
