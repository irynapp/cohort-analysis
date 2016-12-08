## Cohort Analysis

### Details

This process is designed to perform a cohort analysis on a set of users/customers. It helps to identify changes in customer ordering behavior based on their signup date.

This process groups customers into 7 day cohorts and then calculates how many distinct customers ordered within X days from their signup date (X is a multiple of 7). Older cohorts have more buckets: 0-6 days, 7-13 days, 14-20 days, etc.

The program expects two csv files: customers and orders.

### Expected Input File Formats

*Customers File Format:*

1. customer id
2. sign up date

*Orders File Format:*

1. id
2. order number
3. customer id
4. order date

### Design Choices/Assumptions

* All dates are stored in UTC format, but groupings are handled in a configurable timezone (ex: PDT).
* Processes only registered users. If order.csv contains user that is not found in customers.csv, this user is dropped.
* Provides list of time zones to choose from.
* Allows user to specify input and output files.
* Default number of cohorts for report is 8; allows user to specify any integer > 0. If the number exceeds number of weeks possible
  to produce based on the custsomers.csv data, the later will be used as max cohort number.
* Cohort ranges are calculated based on the max and min dates in customers.csv
* Number of bucket day ranges (0-6 days, 7-13 days, etc) is based on the number of cohort ranges (number of buckets = number of cohorts)
* All the date related manipulations involve date and time objects (not just date).
* Percent metrics have 2 decimal points - precision is better this way (example: 1.98% instead of 2%)

###Testing

Tested with Python 2.7

#####Test Cases:

* Read none csv files for inputs - failed in both cases as expected.
* Cohort number is 0 - failed as expected.
* Cohort number exceeds number of weeks possible to produce based on the input data - generated report based on the availbale number of weeks from the input data.
* Cohort number is not specified by user - generated csv report of 8 cohorts.
* Cohort number is 5 - generated csv report of 5 cohorts.
* Check correctness of UTC date and time convesions to different time zones (US/Eastern, US/Pacific, US/Central, Australia/Melbourne) - passed
* Verify metric counts for 3 cohorts, 5 cohorts and 8 cohorts - passed (Note: for this purpose I used different code, but when QA code produced by the same
  developer, it is hard to gurantee new aproach to the algorithm)


###Usage:

```
		Usage: cohort_counts.py [options] customers_file orders_file

		Example: cohort_counts.py customers.csv orders.csv -t US/Eastern

Options:
  -h, --help            show this help message and exit
  -o OUTPUT_FILE, --output-file=OUTPUT_FILE
                        Output directory. Default:
                        /Users/irynapp/Desktop/output.csv.
  -c COHORTS_NUMBER, --cohorts-number=COHORTS_NUMBER
                        Number of cohorts to process for report. Default: 8.
  -t TIME_ZONE, --time-zone=TIME_ZONE
                        Time zone to convert UTC dates to. Default:
                        US/Pacific.  Choices: ['Africa/Abidjan',
                        'Africa/Accra', 'Africa/Addis_Ababa',
                        'Africa/Algiers', 'Africa/Asmara', 'Africa/Bamako',
                        'Africa/Bangui', 'Africa/Banjul', 'Africa/Bissau',
                        'Africa/Blantyre', 'Africa/Brazzaville',
                        'Africa/Bujumbura', 'Africa/Cairo',
                        ....
                        'US/Alaska', 'US/Arizona', 'US/Central', 'US/Eastern',
                        'US/Hawaii', 'US/Mountain', 'US/Pacific', 'UTC']

Usage Example:

	python cohort_counts.py customers.csv orders.csv

	python cohort_counts.py customers.csv orders.csv -o /Users/irynapp/Desktop/output_three_cohorts.csv -c 3

	python cohort_counts.py customers.csv orders.csv -t Australia/Melbourne

```
### Output Examples

Output examples are provided in output_exampels directory:
* output.csv
* output_30_cohorts.csv
* output_3_cohorts.csv