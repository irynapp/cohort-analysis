from __future__ import division

import collections
import csv
import datetime
import os 
import pytz

from optparse import OptionParser


class CohortCounts(object):
	"""
	Provide functionality to perform a cohort analysis
	on customers based on their signup date.
	"""
	def __init__(self, cohorts_number, time_zone):
		"""
		Save options needed to perform analysis.

		:param cohorts_number: Number of cohorts to perform analysis for.
		:param time_zone: Time zone to convert UTC input data dates.
		"""
		self.cohorts_number = cohorts_number
		self.time_zone = time_zone

	def read_csv_file(self, file):
		"""
		Process csv file by removing its header
		and yielding rest of the lines.

		:param file: Csv file to process.
		"""
		with open(file) as fh:
			reader = csv.reader(fh)
			# Remove file header
			next(reader, None)
			for line in reader:
				yield line

	def process_customers(self, customers_file):
		"""
		Process customers data and identify earliest and latest
		registration dates. Customers data will be stored as
		{ user_id: date, }.

		:param customers_file: Customers data to process.
		"""
		min = max = None
		customers = {}
		try:
			for user_id, date_str in self.read_csv_file(customers_file):
				date = self.convert_date(date_str)
				min, max = self.min_max_date(min, max, date)
				customers[user_id] = date
		except ValueError:
			raise Exception('Customers file has unexpected format.')

		self.customers = customers
		self.min = min
		self.max = max

	def process_orders(self, orders_file):
		"""
		Process orders data. Orders data will be stored as 
		{ user_id: [order_date, ], }.

		:param orders_file: Orders data to process.
		"""
		orders = collections.defaultdict(list)
		try:
			for _, _, user_id, date_str in self.read_csv_file(orders_file):
				date = self.convert_date(date_str)
				orders[user_id].append(date)
		except ValueError:
			raise Exception('Orders file has unexpected format.')

		self.orders = orders

	def min_max_date(self, min, max, date):
		"""
		Identify earliest and latest dates.

		:param min: Previous earliest date.
		:param max: Previous latest date.
		:param date: Date to compare to earliest and latest dates.
		:returns: Newly identified earliest and latest dates.
		"""
		if not min or min > date:
			min = date

		if not max or max < date:
			max = date

		return min, max

	def convert_date(self, date_str):
		"""
		Convert UTC date to this object time zone date.

		:param date_str: UTC date string to convert.
		returns: Date object converted based on the object's time zone.
		"""
		date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
		date_obj = date_obj.replace(tzinfo=pytz.timezone('UTC'))
		return date_obj.astimezone(pytz.timezone(self.time_zone))

	def build_default_output(self):
		"""
		Define output structure with specific ordering
		and default values and save possible cohorts for later use.

		:returns: Output structure with specific ordering
			and default values.

		Output format:
		{
			(cohort_date1, cohort_date2): {
				customers: 0,
				(0, 6): {
					total: set(uid, ),
					first_time: set(uid, ),
				},
				(7, 13): {..},
				..
			},
			..
		}
		"""
		# To simplify writing data into final output file in specific order,
		# store rows and columns headers in specific order. 
		cohorts_data = collections.OrderedDict()
		start = end = self.max
		count = 1
		while count <= self.cohorts_number and end > self.min:
			start = end - datetime.timedelta(days=6)
			cohorts_data[(start, end)] = None
			end = start - datetime.timedelta(days=1)
			count += 1

		# Save available cohorts for later use.
		self.cohorts = cohorts_data.keys()
		cohorts_data = self.add_default_cohort_values(cohorts_data)
		return cohorts_data

	def add_default_cohort_values(self, cohorts_data):
		"""
		Add columns with default values to the output structure
		in specific order and save possible day ranges (buckets) for later use.

		:param cohorts_data: Output structure to add columns to.
		:returns: Modified output structure.
		"""
		total_cohorts = len(self.cohorts)
		
		for cohort in self.cohorts:
			cohorts_data[cohort] = collections.OrderedDict()
			cohorts_data[cohort]['customers'] = 0
			count = 0
			for i in range(total_cohorts):
				if count % 7 == 0:
					cohorts_data[cohort][(count,  count + 6)] = {
						'total': set(),
						'first_time': set(),
					}
					count += 7

		# Save available day ranges (buckets) for later use.
		self.day_ranges = [key for key in cohorts_data[cohort] if key != 'customers']
		return cohorts_data

	def is_cohort_user(self, cohort, reg_date):
		"""
		Check if the given user registration date belongs
		to the given cohort's date range.

		:param cohort: Cohort's date range to check against.
		:param reg_date: User registration date to check.
		:returns: True if user is registered within the cohort's date range;
			false, otherwise.
		"""
		if reg_date >= cohort[0] and reg_date <= cohort[1]:
			return True
		return False

	def get_cohort_users(self, cohort):
		"""
		Pull list of users registered in the
		given cohort's date range.

		:param cohort: Cohort's date range to run on.
		:returns: List of users registered within the 
			cohort's date range.
		"""
		users = []
		for user, reg_date in self.customers.items():
			if self.is_cohort_user(cohort, reg_date):
				users.append(user)
		return users

	def get_day_range(self, order_date, reg_date):
		"""
		Get column day range (bucket) based on the specified
		user's order date and registration date.

		:param order_date: User's order date to run on.
		:param reg_date: User's registration date to run on.
		:returns: Day range column order belongs to.
		"""
		days = (order_date - reg_date).days
		for day_range in self.day_ranges:
			if days >= day_range[0] and days <= day_range[1]:
				return day_range
		return []

	def generate_output(self):
		"""Generate counts for each available cohort."""
		output = self.build_default_output()
		# For each cohort:
		# - Get its users
		# - Calculate number of users in the cohort
		# - For each cohort user, identify a bucket each user's order
		# 	belongs to and add this user to appropriate bucket
		for cohort in self.cohorts:
			cohort_users = self.get_cohort_users(cohort)
			output[cohort]['customers'] = len(cohort_users)

			for user in cohort_users:
				user_reg_date = self.customers[user]
				user_orders = sorted(self.orders.get(user, []))
				# Drop users with no orders.
				if not user_orders:
					continue

				# Process first order.
				day_range = self.get_day_range(user_orders[0], user_reg_date)
				# Drop users with orders that do not belong to any day ranges;
				# orders are sorted, so once out of range order is found, rest
				# of them will be also out of range.
				if not day_range:
					continue
				output[cohort][day_range]['first_time'].add(user)

				# Process remaining orders.
				for order in user_orders:
					day_range = self.get_day_range(order, user_reg_date)
					# Drop users with orders that do not belong to any day ranges;
					if not day_range:
						break
					output[cohort][day_range]['total'].add(user)

		# Save output for further processing.
		self.output = output
	
	def write_output(self, output_file):
		"""
		Write output to the specified output file.

		:param output_file: Output file to run on.
		"""
		# Create csv file header.
		header = ['Cohort', 'Customers',]
		for start, end in self.day_ranges:
			day_range_str = '{}-{} days'.format(start, end)
			header.append(day_range_str)

		with open(output_file, 'wb') as fh:
			writer = csv.writer(fh)
			writer.writerow(header)
			for cohort, cohort_value in self.output.items():
				writer.writerow(
					self.build_row(cohort, cohort_value)
				)

	def build_row(self, cohort, cohort_value):
		"""
		Calculate cohort's counts, format outputs
		and build the row for each given cohort and
		its values.

		:param cohort: Cohort to build row for.
		:param cohort_value: Cohort Value to build row for.
		:returns: Cohort's row populated with data. 
		"""
		cohort_str = '{}-{}'.format(
			cohort[0].strftime('%m/%d'),
			cohort[1].strftime('%m/%d'),
		)

		customers = cohort_value.pop('customers')
		customers_str = '{} customers'.format(customers)
		
		row = [
			cohort_str, 
			customers_str,
		]

		for day_range_dict in cohort_value.values():
			# Total orders in the given cohort.
			orders = len(day_range_dict['total'])
			total_str = '{:.2f}% orderers ({})'.format(
				self.calculate_percent(customers, orders),
				orders,
			)

			# Total first time orders in the given cohort.
			first_time_orders = len(day_range_dict['first_time'])
			first_time_str = '{:.2f}% 1st time ({}) '.format(
				self.calculate_percent(customers, first_time_orders),
				first_time_orders,
			)
			# Skip rows with no mettrics.
			if orders or first_time_orders:
				row.append(total_str + '\n' + first_time_str)

		return row


	def calculate_percent(self, total_number, some_number):
		"""
		Calculate percent for the specified number.

		:param total_number: Total value to run on.
		:param some_number: Number to calculate percent for.
		:returns: Percent for the specified number.
		"""
		return (some_number * 100) / total_number

		
if __name__ == '__main__':
	dir_path = os.path.dirname(os.path.realpath(__file__))
	time_zones = [tz for tz in pytz.common_timezones]

	helper_string = """
		Usage: %prog [options] customers_file orders_file\n
		Example: %prog customers.csv orders.csv -t US/Eastern
	"""

	parser = OptionParser(usage=helper_string)

	parser.add_option(
		'-o', '--output-file', action='store', dest='output_file',
		default=os.path.join(dir_path, 'output.csv'), type='string',
		help='Output directory. Default: %default.'
	)

	parser.add_option(
		'-c', '--cohorts-number', action='store',
		dest='cohorts_number', default=8, type='int',
		help='Number of cohorts to process for report. Default: %default.'
	)

	parser.add_option(
		'-t', '--time-zone', action='store', dest='time_zone',
		default='US/Pacific', type='choice', choices=time_zones,
		help='Time zone to convert UTC dates to. Default: %default. \nChoices: {}'.format(time_zones)
	)

	(options, args) = parser.parse_args()

	if len(args) != 2:
		parser.error("Process requires csv customers and orders files!")

	customers_file, orders_file = args
	output_file = options.output_file
	cohorts_number = options.cohorts_number
	time_zone = options.time_zone

	if cohorts_number < 1:
		parser.error("Number of cohorts must be larger than 0!")

	obj = CohortCounts(cohorts_number, time_zone)
	obj.process_customers(customers_file)
	obj.process_orders(orders_file)
	obj.generate_output()
	obj.write_output(output_file)