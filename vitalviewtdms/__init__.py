from nptdms import TdmsFile
import sys
import numpy
import datetime
import time

def dt64_to_utc(v):
	"""
	Convert numpy.datetime64 object to a python native datetime.datetime object.
	Assumes @v is a local time and that that local time is the same timezone offset as the machine running this code.
	"""
	# https://stackoverflow.com/questions/13703720/converting-between-datetime-timestamp-and-datetime64
	ts = (v - numpy.datetime64('1970-01-01T00:00:00')) / numpy.timedelta64(1, 's')
	dt = datetime.datetime.fromtimestamp(ts)

	# calculate epoch offset
	epoch = time.mktime(dt.timetuple())
	offset = datetime.datetime.fromtimestamp(epoch) - datetime.datetime.utcfromtimestamp(epoch)

	# Subtract timezone offset and force to UTC
	return (dt - offset).replace(tzinfo=datetime.timezone.utc)

def nonecoerce(v):
	"""Convert numpy.nan to python None"""
	if numpy.isnan(v):
		return None
	else:
		return v

def VitalViewTDMS_to_py(fname):
	"""
	Reads data from a VitalView 6.0 TDMS file a @fname and returns a dictionary of animal name -> 2-tuple of (column names, data).
	Where column names are Time, Heart Rate, Temperature, and/or Activity in some order.
	Where data is a list of tuples of the data in the same order as in the column names.

	Time is a datetime.datetime object.
	Heart rate is a float in beats per minute.
	Activity is a float of arbitrary units.
	Temperature is a float in degress Celcius.
	"""

	with TdmsFile.read(fname) as tdms_file:
		# Get time stamps
		group = tdms_file['System']
		channel = group['Time']
		times = channel[:]
		times = [dt64_to_utc(_) for _ in times]

		# Map animal name to 2-tuple of (column names, data)
		ret = {}

		# Should have "System" and "Event", the rest should be animals
		for cname in tdms_file.groups():
			# Just the name, thanks
			cname = cname.name

			if cname in ('System', 'Event'):
				continue

			# Get channel information
			group = tdms_file[cname]

			# May be any subset of ('Heart Rate', 'Temperature', 'Activity')
			raw_data = {}
			for k in ('Heart Rate', 'Temperature', 'Activity'):
				z = group[k]
				z = [nonecoerce(_) for _ in z]
				raw_data[k] = z

			# Iterate over all the times in the file and match to the data that's available
			cols = list(raw_data.keys())
			r = []
			for idx,t in enumerate(times):
				z = [t]
				for k in cols:
					z.append(raw_data[k][idx])
				r.append(tuple(z))
			
			# Return a list of columns and list of datapoints as a 2-tuple
			cols = tuple(['Time'] + cols)
			ret[cname] = (cols,r)

		# Example:
		# {
		#   '111-1': {
		#     ('Time', 'Heart Rate', 'Activity'),
		#     [
		#       (datetime(...), 200, 0.5),
		#       (datetime(...), 201, 0.1),
		#     ],
		#   },
		# }
		return ret

if __name__ == '__main__':
	d = VitalViewTDMS_to_py(sys.argv[1])
	for aname,data in d.items():
		print("Animal: %s" % aname)

		idx_t =  data[0].index('Time')
		idx_hr = data[0].index('Heart Rate')
		idx_act =data[0].index('Activity')
		idx_t =  data[0].index('Temperature')

		hr = [0, 0]
		act = [0, 0]
		t = [0, 0]
		for _ in data[1]:
			if _[idx_hr] is not None:
				hr[0] += 1
				hr[1] += _[idx_hr]
			if _[idx_act] is not None:
				act[0] += 1
				act[1] += _[idx_act]
			if _[idx_t] is not None:
				t[0] += 1
				t[1] += _[idx_t]

		print("Heart rate:")
		if hr[0] == 0:
			print("  N:   %d" % hr[0])
		else:
			print("  N:   %d" % hr[0])
			print("  Sum: %.2f" % hr[1])
			print("  Avg: %.2f" % (hr[1] / hr[0]))

		print("Activity:")
		if act[0] == 0:
			print("  N:   %d" % act[0])
		else:
			print("  N:   %d" % act[0])
			print("  Sum: %.2f" % act[1])
			print("  Avg: %.2f" % (act[1] / act[0]))

		print("Temperature:")
		if t[0] == 0:
			print("  N:   %d" % t[0])
		else:
			print("  N:   %d" % t[0])
			print("  Sum: %.2f" % t[1])
			print("  Avg: %.2f" % (t[1] / t[0]))

