choice = input("Edit with computer (0) or edit with terminal (1)")
if choice != 0 and choice != 1:
	_ = input("Invalid selection")
	quit()
new_state = "False" if choice == 1 else "True"
new_boot = f'''
import storage
storage.remount('/', {new_state})
'''

with open('boot.py', 'w') as f:
	f.write(new_boot)
