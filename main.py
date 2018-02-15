# Copyright (c) 2018 Zhihao Yao (z.yao@uci.edu)
#
# This program is mean to be a single-file script to clean up 
# our projects. It is not written in an 'objective programming' 
# fashion. If you want it that way, please do it yourself.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import re
import sys

STR_COMMENT = r'//'
STR_BASH_COMMENT = r'#'
STR_PRINT = r'(PRINT|FPRINTF|FPRINTF_COND|' + \
	r'PRINTK|STACK_TRACE|PRINTF|PRINTF_COND|' + \
	r'PRINTK_STUB|PRINTK_COND|DUMP_STACK|' + \
	r'DUMP_STACK_COND|LPRINTK)'
STR_BLOCK_COMMENT_START = r'/*'
STR_BLOCK_COMMENT_END = r'*/'
STR_DIFF_FILE_FLAG = r'diff --git'
STR_DIFF_SEGMENT_FLAG = r'(@@.+@@.*\n)'
STR_DIFF_SEGMENT_INDICATOR = r'@@'

REGEX_NEW_PRINTS_FULL = r'\+(\s*)' + \
					STR_PRINT + \
					r'.?\(.*\)(\s)*;{1}'
REGEX_NEW_PRINTS_BEGIN = r'\+(\s*)' + \
					STR_PRINT + r'.?\('
REGEX_FUNCTION_CALL_END = r'.*\)\s*;{1}\s*$'
REGEX_NEW_COMMENT = r'\+(\s*)' + STR_COMMENT
REGEX_NEW_BASH_COMMENT = r'\+(\s*)' + STR_BASH_COMMENT
REGEX_CONCATENATE = r'\S;(?![^(]*\))'
REGEX_C_CPP_FILENAME = r'(\.c.*)|(\.h.*)|(\.i.*)|(\.t.*)'
REGEX_EXCEPTION_URL = r"""(("|').*\/\/.*("|'))|(.*:\/\/)"""
REGEX_EXCEPTION_IF = r'([^#](if|for|while|do|switch)[ \(])|(else)'

MSG_ERROR = 'ERROR: '
MSG_BAD_CODE = 'You should not code this way'

def get_command_line_args():
	result = {}
	argv = sys.argv
	while argv:
		if argv[0][0] == '-':
			result[argv[0]] = argv[1]
		argv = argv[1:]
	if '-i' not in result:
		result['-i'] = 'git.diff'
	if '-o' not in result:
		result['-o'] = 'out.diff'
	return result

def number_of_regex_matched(p, s):
	assert type(p) is str
	assert type(s) is str
	return len(re.findall(p, s))

def get_non_comment_line_content(line):
	assert type(line) is str
	return line[:line.find(STR_COMMENT)]

def list_to_string(l):
	assert type(l) is list
	return ''.join(l)

def line_is_diff(l):
	assert type(l) is str
	return l.startswith('+') or l.startswith('-')

def cramp_segment(segment):
	assert type(segment) is str
	segment_list = segment.splitlines()
	result = ''
	has_seen_diff = False
	total_delta = 0
	front_delta = 0

	for i in range(len(segment_list)):
		if line_is_diff(segment_list[i]) and not has_seen_diff:
			has_seen_diff = True

		if line_is_diff(segment_list[i]):
			result += segment_list[i] + '\n'
			continue
		# context lines
		if (i-1 >= 0 and line_is_diff(segment_list[i-1])) or \
			(i-2 >= 0 and line_is_diff(segment_list[i-2])) or \
			(i-3 >= 0 and line_is_diff(segment_list[i-3])) or \
			(i+1 <= len(segment_list)-1 and line_is_diff(segment_list[i+1])) or \
			(i+2 <= len(segment_list)-1 and line_is_diff(segment_list[i+2])) or \
			(i+3 <= len(segment_list)-1 and line_is_diff(segment_list[i+3])):
			result += segment_list[i] + '\n'
			continue

		# count removed lines
		if not has_seen_diff:
			front_delta += 1
		total_delta += 1

		# result += line + '\n'
	return {"front_delta": front_delta, \
		"total_delta": total_delta, \
		"result": result}

def load_file_as_string(filepath):
	file_content = ''
	with open(filepath) as fd:
		file_content = fd.read()
	return file_content

def find_index_of_subtring(s, substring, occr, overlap = False):
	assert type(s) is str
	assert type(substring) is str
	assert type(occr) is int
	index = s.find(substring)
	while index >= 0 and occr > 1:
		increment = (1 if overlap else len(substring))
		index = s.find(substring, index+ increment)
		occr -= 1
	return index

def split_str_into_list_by_regex_delimiter(s, delimiter, prefix = 'nul'):
	assert type(s) is str
	if prefix == 'nul': prefix = delimiter
	compiled_regex = re.compile(delimiter)
	result = []
	for i in compiled_regex.split(s):
		if len(i.strip()) == 0: continue
		result.append(prefix + i)
	return result

def remove_last_new_line(s):
	assert type(s) is str
	if len(s) == 0: return ''
	if s[-1] in ['\n', '\r']:
		return s[:-1]
	else:
		return s

def delta_segment_header(s, sd, fd, ch, ct):
	assert type(s) is str
	assert type(sd) is int
	assert type(fd) is int
	# there are four cases, +/- xx without comma means the offset is one
	# e.g. @@ -xx,xx +xx @@
	#	   @@ -xx,xx +xx,xx @@
	#	   @@ -xx +xx,xx @@
	#	   @@ -xx +xx @@
	if s.find(',', 0, find_index_of_subtring(s,' ',2)) != -1:
		i_start = s[s.find('-')+1:s.find(',')]
		i_offset = s[s.find(',')+1:find_index_of_subtring(s,' ',2)]
	else:
		i_start = s[s.find('-')+1:find_index_of_subtring(s,' ',2)]
		i_offset = -1
	if s.find(',', find_index_of_subtring(s,' ',2), len(s)) != -1:
		o_start = s[s.find('+')+1:\
		s.find(',', find_index_of_subtring(s,' ',2), len(s))]
		o_offset = s[s.find(',', find_index_of_subtring(s,' ',2), len(s))+1:\
		find_index_of_subtring(s,' ',3)]
	else:
		o_start = s[s.find('+')+1:find_index_of_subtring(s,' ',3)]
		o_offset = -1

	i_start = int(i_start) + ch;
	i_offset = int(i_offset) - ct;
	o_start = int(o_start) - fd + ch;
	o_offset = int(o_offset) - sd - ct;

	result = STR_DIFF_SEGMENT_INDICATOR + \
		' -' + str(i_start) + \
		(',' + str(i_offset) if i_offset >= 0 else '') + \
		' +' + str(o_start) + \
		(',' + str(o_offset) if o_offset >= 0 else '') + \
		' ' + STR_DIFF_SEGMENT_INDICATOR
	# print i_start
	# print i_offset
	# print o_start
	# print o_offset
	return result + '\n'

def IS_NEW_LINE(line):
	assert type(line) is str
	return line.startswith('+')

def IS_EMPTY_LINE(line):
	assert type(line) is str
	return len(line[1:].strip()) == 0

def IS_UNCHANGED_LINE(line):
	assert type(line) is str
	return line.startswith(' ')

def IS_CONCATENATED(line):
	assert type(line) is str
	return number_of_regex_matched(REGEX_CONCATENATE, line) >=2

def IS_C_TYPE_FILE(line, per_file_header):
	assert type(line) is str
	assert type(per_file_header) is str
	if number_of_regex_matched(REGEX_C_CPP_FILENAME, per_file_header):
		return True
	else:
		return False

def CHECK_IF_NEW_LINE_IS_COMMENT(line):
	assert type(line) is str
	return number_of_regex_matched(REGEX_NEW_COMMENT, line)

def CHECK_IF_NEW_LINE_IS_BASH_COMMENT(line, per_file_header):
	assert type(line) is str
	assert type(per_file_header) is str
	if number_of_regex_matched(REGEX_C_CPP_FILENAME, per_file_header):
		return False
	return number_of_regex_matched(REGEX_NEW_BASH_COMMENT, line)

def CHECK_IF_LINE_CONTAINS_ANY_COMMENT(line):
	assert type(line) is str
	return STR_COMMENT in line

def CHECK_IF_NEW_LINE_CONTAINS_ANY_COMMENT(line):
	assert type(line) is str
	if number_of_regex_matched(REGEX_EXCEPTION_URL, line):
		return False
	return IS_NEW_LINE(line) and STR_COMMENT in line

def CHECK_IF_NEW_LINE_IS_DEBUG_PRINTS(line):
	assert type(line) is str
	return number_of_regex_matched(REGEX_NEW_PRINTS_FULL, line)

def CHECK_IF_NEW_OR_ORIGINAL_EMPTY_LINE(line):
	assert type(line) is str
	return (IS_NEW_LINE(line) or IS_UNCHANGED_LINE(line)) and \
	IS_EMPTY_LINE(line)

def CHECK_IF_NEW_EMPTY_LINE(line):
	assert type(line) is str
	return IS_NEW_LINE(line) and IS_EMPTY_LINE(line)

def CHECK_IF_PREVIOUS_NEW_LINE_HEADLESS(line):
	assert type(line) is str
	return not line[1:].strip().startswith('#') and \
	not line[1:].strip().startswith('/') and IS_NEW_LINE(line) and \
	number_of_regex_matched(REGEX_EXCEPTION_IF, line) and not \
	(line.strip().endswith(';') or line.strip().endswith('{'))

def CHECK_IF_MULTIPLE_NEW_EMPTY_LINES(line, previous_line):
	assert type(line) is str and type(previous_line) is str
	return CHECK_IF_NEW_EMPTY_LINE(previous_line) and \
	CHECK_IF_NEW_EMPTY_LINE(line)

def CHECK_IF_NEW_MULTIPLE_LINE_PRINTS_START(line):
	assert type(line) is str
	return number_of_regex_matched(REGEX_NEW_PRINTS_BEGIN, line) and not \
	number_of_regex_matched(REGEX_FUNCTION_CALL_END, line)

def CHECK_IF_NEW_MULTIPLE_LINE_PRINTS_END(line):
	assert type(line) is str
	return number_of_regex_matched(REGEX_FUNCTION_CALL_END, line)

def ASSERT_NO_NEW_LINE_CONCATENATED(line):
	assert type(line) is str
	line = line[1:]
	assert not IS_NEW_LINE(line) or not IS_CONCATENATED(line)

def ASSERT_NO_NEW_PRINTS_ACROSS_MULTIPLE_LINES(line):
	assert type(line) is str
	assert not number_of_regex_matched(REGEX_NEW_PRINTS_BEGIN, line) or \
	number_of_regex_matched(REGEX_FUNCTION_CALL_END, line)

def ASSERT_NO_NEW_BLOCK_COMMENT(line):
	assert type(line) is str
	assert STR_BLOCK_COMMENT_START not in line and \
	STR_BLOCK_COMMENT_END not in line

args = get_command_line_args()
filepath = args['-i']
# output to file is not implemented

diff_file_content = load_file_as_string(filepath)
diff_list_by_file = \
split_str_into_list_by_regex_delimiter(diff_file_content, STR_DIFF_FILE_FLAG)

for per_file in diff_list_by_file:
	diff_list_by_segment = \
	split_str_into_list_by_regex_delimiter(per_file, STR_DIFF_SEGMENT_FLAG, '')
	file_result = ''
	all_segment_result = ''
	file_delta = 0

	per_file_header = diff_list_by_segment[0]
	# print "DEBUG: file header\n" + per_file_header
	diff_list_by_segment = diff_list_by_segment[1:]
	# print diff_list_by_segment

	assert not len(diff_list_by_segment) % 2

	for segment_index in range(len(diff_list_by_segment) / 2):
		segment_header = diff_list_by_segment[segment_index * 2]
		segment_string = diff_list_by_segment[segment_index * 2 + 1]
		segment_result = ''
		segment_delta = 0

		inside_multi_line_comment = False
		previous_line = '.'
		for line in segment_string.splitlines():

			if CHECK_IF_MULTIPLE_NEW_EMPTY_LINES(line, previous_line):
				segment_delta += 1
				continue

			# check if we are in a multi-line comment
			if inside_multi_line_comment:
				segment_delta += 1
				inside_multi_line_comment = \
				not CHECK_IF_NEW_MULTIPLE_LINE_PRINTS_END(line)
				continue

			if (CHECK_IF_NEW_MULTIPLE_LINE_PRINTS_START(line) or \
				CHECK_IF_NEW_LINE_IS_DEBUG_PRINTS(line)) and \
				CHECK_IF_PREVIOUS_NEW_LINE_HEADLESS(previous_line):
				print MSG_ERROR + MSG_BAD_CODE
				print previous_line.strip()
				print line.strip()
			# 	assert(False)

			# remove new comments
			if CHECK_IF_NEW_MULTIPLE_LINE_PRINTS_START(line):
				inside_multi_line_comment = True
				segment_delta += 1
				continue
			elif CHECK_IF_NEW_LINE_IS_COMMENT(line) or \
			CHECK_IF_NEW_LINE_IS_BASH_COMMENT(line, per_file_header):
				segment_delta += 1
				continue
			elif CHECK_IF_NEW_LINE_CONTAINS_ANY_COMMENT(line) and \
			IS_C_TYPE_FILE(line, per_file_header):
				line = get_non_comment_line_content(line)

			# remove new debug logs
			if CHECK_IF_NEW_LINE_IS_DEBUG_PRINTS(line):
				segment_delta += 1
				continue

			previous_line = line
			segment_result += line + '\n'

		cramp_result = cramp_segment(segment_result)
		segment_result_dry = cramp_result["result"]
		if len(segment_result_dry) == 0:
			segment_result = ''

		segment_header = delta_segment_header(segment_header, \
											segment_delta, \
											file_delta, \
											0, 0)
		segment_result = (segment_header + segment_result) \
		if len(segment_result) != 0 else ''
		all_segment_result += segment_result
		file_delta += segment_delta
		# print segment_result

	file_result += (per_file_header + all_segment_result) \
	if len(all_segment_result) != 0 else ''
	file_result = remove_last_new_line(file_result)
	if len(file_result) != 0:
		print file_result