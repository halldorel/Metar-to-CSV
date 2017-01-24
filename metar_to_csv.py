from metar import Metar

import sys, getopt

# Delimiter used is exported CSV file
global DELIM
DELIM = ";"

# Delimiters in input CSV
# Input CSV should have two columns, first column is date and
# second is the METAR string.
global INPUT_DELIM
INPUT_DELIM = ";"

class SplitMetarLine():
	"""A SplitMetarLine object is a single row of parsed values
	to be exported in a CSV file. It can be thought of as a 'View'."""
	def __init__(self, pars, date):	
		self.parsed = pars
		self.columns = {}
		self.date = date

		# Tuple contains column name at index 0
		# and lambda for retrieving value or value at index 1
		def uw(a):
			if a:
				return a
			else:
				return ""

		# To add a column to the output CSV, add a tuple in this list
		# with first item as a description string, and second 
		# item can be a lambda that is executed on the value
		# if we want to transform it in some way, or just None if 
		# we want the raw value from the parser.
		self.layout = [
			("DATE", lambda x: self.date),
			("METAR", lambda x: x.rstrip()),
			("STATUS", None),
			("D", None),
			("F", None), 
			("FG", None),
			("WIND_DIR_FROM", None),
			("WIND_DIR_TO", None),
			("VRB", lambda x: "1" if x else ""),
			("V1", None),
			("VD", None),
			("MAX_VIS", None),
			("MAX_VIS_DIR", None),
			("RUNWAY", None),
			("RUNWAY_HIGH", None),
			("RUNWAY_LOW", None),
			("WEATHER", lambda x: (" ".join([uw(a[0]) + uw(a[1]) +\
				uw(a[2]) + uw(a[3]) + uw(a[4]) for a in x]))),
			("FEW", None),
			("SCT", None),
			("BKN", None),
			("BKN_2", None),
			("OVC", None),
			("VV", None),
			("Q", None),
			("RECENT", lambda x: (" ".join([uw(a[0]) + uw(a[1]) +\
				uw(a[2]) + uw(a[3]) + uw(a[4]) for a in x]))),
			("TCU", None),
			("CB", None)
		]

	def __repr__(self):
		ret = ""
		for key, value in self.columns.items() :
		    ret = ret + key + ": " + str(value) + " "
		return ret

	def has_column(self, column_name):
		return column_name in self.columns

	def add_item(self, x, name):
		"""Adds a key-value pair (name -> x) to the Metar Line object,
		corresponding to one cell in the CSV file.
		"""
		if callable(getattr(x, "value", None)):
			self.columns[name] = int(x.value())
		elif x is not None:
			self.columns[name] = x
		else:
			self.columns[name] = ""

	def header(self):
		"""Prints header for the CSV"""
		return DELIM.join([x[0] for x in self.layout]) + "\n"

	def to_csv(self):
		"""Prints the MetarLine object as
		delimited CSV line"""
		return DELIM.join([str(x[1](self.columns[x[0]]) if callable(x[1]) else self.columns[x[0]]) if self.has_column(x[0]) else "" for x in self.layout])

def add_line(date, metar_string, error=False):
	"""Create a SplitMetarLine object, and feed it with key/value pairs."""
	if error:
		metarline = SplitMetarLine(None, date)
		metarline.add_item(date, "DATE")
		metarline.add_item(metar_string, "METAR")
		metarline.add_item("Error", "STATUS")
		return metarline
	split = Metar.Metar(metar_string)
	metarline = SplitMetarLine(split, date)

	metarline.add_item(date, "DATE")

	metarline.add_item(split.code, "METAR")
	metarline.add_item("OK", "STATUS")
	metarline.add_item(split.press, "Q")

	metarline.add_item(split.wind_dir, "D")
	metarline.add_item(split.wind_speed, "F")
	metarline.add_item(split.wind_gust, "FG")

	metarline.add_item(split.vrb, "VRB")
	metarline.add_item(split.wind_dir_from, "WIND_DIR_FROM")
	metarline.add_item(split.wind_dir_to, "WIND_DIR_TO")

	metarline.add_item(split.vis, "V1")
	metarline.add_item(split.vis_dir, "VD")

	metarline.add_item(split.max_vis, "MAX_VIS")
	metarline.add_item(split.max_vis_dir, "MAX_VIS_DIR")

	if len(split.runway) > 0:
		name, low, high = split.runway[0]

		metarline.add_item(name, "RUNWAY")
		metarline.add_item(low, "RUNWAY_LOW")
		metarline.add_item(high, "RUNWAY_HIGH")

	metarline.add_item(split.weather, "WEATHER")
	metarline.add_item(split.recent, "RECENT")

	broken = 1

	for item in split.sky:
		cover = item[0]
		height = item[1]
		cloud = item[2]

		metarline.add_item(split.sky, "SKY")

		if cover:
			if cover == 'BKN' and broken > 1:
				metarline.add_item(height, cover + "_" + str(broken))

			else:
				metarline.add_item(height, cover)

			if cloud == 'TCU' or cloud == 'CB':
				metarline.add_item(1, cloud)

			if cover == 'BKN':
				broken = broken + 1

		if cloud and not metarline.has_column("CLOUD"):
			metarline.add_item(cloud, "CLOUD")

	metarline.add_item(split.temp, "T")
	metarline.add_item(split.dewpt, "TD")
	metarline.add_item(split.press_sea_level, "QNH")

	return metarline

def open_files_and_parse(infile, outfile, errorfile="errors.txt"):
	output = []
	messages = []
	errors = []

	print("Reading from " + infile)

	with open(infile, 'r') as f:
		read_data = f.readlines()

		for line in read_data:
			if INPUT_DELIM not in line:
				errors.append("Missing date field" + "; " + line)
				continue
				# raise Exception('Missing date field')
			date = line.split(INPUT_DELIM)[0]
			metar_string = line.split(INPUT_DELIM)[1]

			try:
				metarline = add_line(date, metar_string)
				messages.append(metarline)
			except Exception as e:
				metarline = add_line(date, metar_string, error=True)
				messages.append(metarline)
				errors.append(str(e) + "; " + metar_string + "\n")

	print("Parsed count: " + str(len(messages)))
	print("Error count: " + str(len(errors)))

	with open (outfile, 'w') as f:
		if len(messages) > 0:
			f.write(messages[0].header())
		for msg in messages:
			f.write(msg.to_csv() + "\n")

	with open (errorfile, 'w') as f:
		for error in errors:
			f.write(error)

def main(argv):
	inputfile = None
	outputfile = "./metar_parsed.csv"

	try: 
		opts, args = getopt.getopt(argv,"hi:o:",["inputfile=","outputfile="])
	except getopt.GetoptError:
		print ('metar_to_csv.py -i <inputfile> -o <outputfile>')
		sys.exit(2)

	for opt, arg in opts:
		if opt == '-h':
			print ('metar_to_csv.py -i <inputfile> [-o <outputfile>]')
			sys.exit()
		elif opt in ("-i", "--ifile"):
			inputfile = arg
		elif opt in ("-o", "--ofile"):
			outputfile = arg

	if inputfile == None:
		print("Input file argument is required.")
		sys.exit(2)
		
	print("Input: " + inputfile + ", output: " + outputfile)
	open_files_and_parse(inputfile, outputfile)

if __name__ == '__main__':
	main(sys.argv[1:])