import pymongo
# from app import cleaning
from itertools import chain
import mongoengine
import os
import copy
import pandas as pd
import numpy as np
import matplotlib
from matplotlib import pylab

matplotlib.use('Agg')

# setting up connection to database
client = pymongo.MongoClient(f"{os.environ.get('mongodb_host')}/otdatasb?retryWrites=true&w=majority")
db = client['otdatasb']


##################################### CONSTANTS ############################################

TOTAL_STUDENTS = db.user.count_documents({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'grade' : {'$lte' : 12}} ]})
SEMESTER = 'Fall2020'
CLASSES = ['Freshman', 'Sophomore', 'Junior', 'Senior']
CONSOLIDATION_THRESHOLD = 1.5

# safely creates folder for charts to be saved
def safe_mkdir(path):
    try:
        os.mkdir(path)
    except FileExistsError:
        print(f"The Folder {path} already exists")
    except Exception as error:
        print(f"error line 231 in charts.py: {error}")
    return path

safe_mkdir('./app/static/' + SEMESTER)

# Aeries ethnicity classifications
ethnicities = [
    'Hispanic or Latino', 'White (not Hispanic)', 'Black or African American', 'Chinese', 'Filipino', 'Japanese', 'Cambodian', 'Korean', 
    'Vietnamese', 'Asian Indian', 'Hmong', 'Laotian', 'Other Asian', 'Samoan', 'Hawaiian', 'Guamanian', 'Other Pacific Islander', 
    'American Indian or Alaskan Native', 'Other or Not Specified'
]
# ethnicity sub-categories (for consolidating into "Other Asian" and "Other Pacific Islander")
Asian_ethnicities = ['Chinese', 'Filipino', 'Japanese', 'Cambodian', 'Korean', 'Vietnamese', 'Asian Indian', 'Hmong', 'Laotian']
Pacific_Islander_ethnicities = ['Samoan', 'Hawaiian', 'Guamanian']


# could be a dictionary?
genders = ['M', 'F', 'N']
gender_words = ['Male', 'Female', 'Nonbinary']

# master list of zip codes queried from database
zip_codes = db.user.distinct('azipcode', filter = {'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'grade' : {'$lte' : 12}} ]})

# language fluency and SPED classifications
lang_fluencies = ['English Only', 'English Learner', 'Initially Fluent (IFEP)', 'Redesignated (RFEP)', 'To Be Determined (TBD)']
sped = ['Inclusion', 'RSP (Resource Specialist Program)', 'SDC (Special Day Class)', 'Speech Only', 'Other SPED']

# updating the non-academy 10th graders who were labelled as 9th grade houses
# db.user.update_many({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'grade' : {'$lte' : 12}}, 
#                       {'cohort' : {'$in' : ['Oakland Tech-9th Grade Janus', 'Oakland Tech-9th Grade Neptune', 'Oakland Tech-9th Grade Sol']}} ]}, 
#                       {'$set' : {'cohort' : ''}})

# master list of cohorts queried from database
cohorts = db.user.distinct('cohort', filter = {'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'grade' : {'$lte' : 12}} ]})
houses = []
for cohort in cohorts:
    if 'House' in cohort:
        houses.append(cohort)

# removing 'No Academy - SDC' from cohort list because we don't need charts for it
cohorts_for_charts = copy.deepcopy(cohorts)
try:
    cohorts_for_charts.remove('No Academy - SDC')
    for house in houses:
        cohorts_for_charts.remove(house)
except:  # case that there are no SDC kids
    pass


COLORS = ['turquoise', 'gold', 'mediumslateblue', 'mediumvioletred', 'dodgerblue', 'chartreuse', 'orange', 'blue', 'indigo']

##################################### HELPER FUNCTIONS ############################################

def calculate_percent(value, total):
    return value / total * 100

# takes in a cursor (iterator) over student User documents
# calculates average GPA of all students in cursor
def average_GPA(students):
    sum = 0
    count = 0
    for student in students:
        sum += student['gpa']
        count += 1
    if count == 0:
        return 0
    return sum / count


# creates a pandas dataframe with the master_list as indexes (row labels) and the following columns:
#       Total Count   Percent    Freshman    Sophomore    Junior    Senior    Freshman GPA    Sophomore GPA    Junior GPA    Senior GPA
# also queries database for blank fields, and adds blank ('') as a row if any exist
def create_master_dataframe(master_list, fieldname):
    blanks = db.user.count_documents({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {fieldname : ''}, {'grade' : {'$lte' : 12}} ]})
    if blanks > 0:
        new_list = master_list + ['']
    else:
        new_list = master_list
    list_of_rows = [] # loop will fill this list!
    for item in new_list: # like 'M' in genders
        row_data = []
        count = db.user.count_documents({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {fieldname : item}, {'grade' : {'$lte' : 12}} ]})
        row_data.append(count)
        row_data.append(calculate_percent(count, TOTAL_STUDENTS))
        row_data.append(db.user.count_documents({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {fieldname : item}, {'grade' : 9} ]}))
        row_data.append(db.user.count_documents({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {fieldname : item}, {'grade' : 10} ]}))
        row_data.append(db.user.count_documents({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {fieldname : item}, {'grade' : 11} ]}))
        row_data.append(db.user.count_documents({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {fieldname : item}, {'grade' : 12} ]}))
        freshmen = db.user.find({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {fieldname : item}, {'grade' : 9}, {'gpa' : { '$exists' : True}} ]}, {'_id': False, 'gpa': True})
        row_data.append(average_GPA(freshmen))
        sophomores = db.user.find({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {fieldname : item}, {'grade' : 10}, {'gpa' : { '$exists' : True}} ]}, {'_id': False, 'gpa': True})
        row_data.append(average_GPA(sophomores))
        juniors = db.user.find({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {fieldname : item}, {'grade' : 11}, {'gpa' : { '$exists' : True}} ]}, {'_id': False, 'gpa': True})
        row_data.append(average_GPA(juniors))
        seniors = db.user.find({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {fieldname : item}, {'grade' : 12}, {'gpa' : { '$exists' : True}} ]}, {'_id': False, 'gpa': True})
        row_data.append(average_GPA(seniors))
        list_of_rows.append(row_data)
    return pd.DataFrame(data = list_of_rows, index = new_list, columns = ['Total Count', 'Percent', 'Freshman', 'Sophomore', 'Junior', 'Senior', 'Freshman GPA', 'Sophomore GPA', 'Junior GPA', 'Senior GPA'])


# takes in a dataframe, groups categories into an "Other" row if the percent of students
# in that category is below a certain threshold (defined above)
##### note: not all dataframes are consolidated!! for gender, ELL, and SPED, we want to see all
#           categories, even if there are 0 people in them
def consolidate_dataframe(dataframe, fieldname):
    to_consolidate = []
    for group in dataframe.index:
        if dataframe.at[group, 'Percent'] < CONSOLIDATION_THRESHOLD:
            to_consolidate.append(group)
    if '' in dataframe.index and '' not in to_consolidate:
        to_consolidate.append('')
    if len(to_consolidate) == 0:
        return
    dataframe.loc['Other'] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # for each column in the dataframe
    for group in to_consolidate: # will create a new row, "Other"
        dataframe.at['Other', 'Total Count'] += dataframe.at[group, 'Total Count']
        dataframe.at['Other', 'Percent'] += dataframe.at[group, 'Percent']
        for year in CLASSES:
            if dataframe.at[group, year] > 0:
                new_GPA = ((dataframe.at['Other', year +' GPA'] * dataframe.at['Other', year] + 
                                dataframe.at[group, year +' GPA'] * dataframe.at[group, year]) / 
                                (dataframe.at['Other', year] + dataframe.at[group, year]))
                dataframe.at['Other', year +' GPA'] = new_GPA
                dataframe.at['Other', year] += dataframe.at[group, year] 
        dataframe.drop(group, inplace = True)

# takes in a dataframe and makes a table! (returns the figure)
# source: https://stackoverflow.com/questions/19726663/how-to-save-the-pandas-dataframe-series-data-as-a-figure/39358752
def render_mpl_table(data, col_width=3.0, row_height=0.625, font_size=14,
                     header_color='#40466e', row_colors=['#f1f1f2', 'w'], edge_color='w',
                     bbox=[0, 0, 1, 1], header_columns=0, row_labels = None, col_labels = None,
                     ax=None, **kwargs):
    if ax is None:
        size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
        fig, ax = matplotlib.pyplot.subplots(figsize=size)
        ax.axis('off')
    if row_labels is None:
        row_labels = data.index
    if col_labels == None:
        col_labels = data.columns
    mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=col_labels, rowLabels = row_labels, **kwargs)
    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(font_size)

    for k, cell in mpl_table._cells.items():
        cell.set_edgecolor(edge_color)
        if k[0] == 0 or k[1] < header_columns:
            cell.set_text_props(weight='bold', color='w')
            cell.set_facecolor(header_color)
        else:
            cell.set_facecolor(row_colors[k[0]%len(row_colors) ])
    return ax.get_figure()


# add a 'total' row to given dataframe that combines all categories
# sum for counts and percentages, weighted average for GPAs
# will create a list with all approporate values, then append it with loc()
def add_totals_row(dataframe):
    totals_row = [
        dataframe['Total Count'].sum(), dataframe['Percent'].sum(), dataframe['Freshman'].sum(), 
        dataframe['Sophomore'].sum(), dataframe['Junior'].sum(), dataframe['Senior'].sum()
    ]
    for year in CLASSES:
        total = dataframe[year].sum()
        if total == 0: # rare case that there are 0 kids in the grade
            totals_row.append(0)
        else:
            GPA_sum = 0
            for group in dataframe.index:
                GPA_sum += dataframe.at[group, year +' GPA'] * dataframe.at[group, year]
            totals_row.append(GPA_sum / total)
    dataframe.loc['All'] = totals_row


# add an 'average GPA' column (average across all classes) to given dataframe
# handles case that it's fall and freshmen don'e have GPAs yet
def add_avgGPA_column(dataframe):
    all_class_GPAs = []
    exclude_freshmen = False
    temp_classes = CLASSES
    if dataframe.at['All', 'Freshman GPA'] == 0:
        exclude_freshmen = True
        temp_classes = CLASSES[1:]  # excludes freshmen
    for group in dataframe.index:
        count = dataframe.at[group, 'Total Count']
        if exclude_freshmen:
            count -= dataframe.at[group, 'Freshman']
        if count == 0:
            all_class_GPAs.append(0)
            continue
        GPA_sum = 0
        for year in temp_classes:
            GPA_sum += dataframe.at[group, year] * dataframe.at[group, year +' GPA']
        all_class_GPAs.append(GPA_sum / count)
    dataframe['Class Avg GPA'] = all_class_GPAs


# cleans data in dataframe - casts count columns to integer, rounds floats to 2 decimal places
def format_data(dataframe):
    dataframe = dataframe.round(2)
    dataframe = dataframe.astype({'Total Count' : 'int32', 'Freshman' : 'int32', 'Sophomore' : 'int32', 'Junior' : 'int32', 'Senior' : 'int32'})
    return dataframe

##################################### CREATING MASTER DATAFRAMES ############################################

# creating gender dataframe
G_masterDF = create_master_dataframe(genders, 'agender')
add_totals_row(G_masterDF)
add_avgGPA_column(G_masterDF)
G_masterDF = format_data(G_masterDF)
print(G_masterDF)


# making the ethnicity dataframe!
E_masterDF = create_master_dataframe(ethnicities, 'aethnicity')

# grouping Asian and Pacific Islander ethnicities (only happens with ethnicity dataframe)
lumped_ethnicities = 0
for ethnicity in Asian_ethnicities:
    if E_masterDF.at[ethnicity, 'Percent'] < 2: # will group this ethnicity with 'Other Asian'
        lumped_ethnicities += 1
        E_masterDF.at['Other Asian', 'Total Count'] += E_masterDF.at[ethnicity, 'Total Count']
        E_masterDF.at['Other Asian', 'Percent'] += E_masterDF.at[ethnicity, 'Percent']
        for year in CLASSES:
            if E_masterDF.at[ethnicity, year] > 0:
                new_GPA = ((E_masterDF.at['Other Asian', year +' GPA'] * E_masterDF.at['Other Asian', year] + 
                                E_masterDF.at[ethnicity, year +' GPA'] * E_masterDF.at[ethnicity, year]) / 
                                (E_masterDF.at['Other Asian', year] + E_masterDF.at[ethnicity, year]))
                E_masterDF.at['Other Asian', year +' GPA'] = new_GPA
                E_masterDF.at['Other Asian', year] += E_masterDF.at[ethnicity, year]           
        E_masterDF.drop(ethnicity, inplace = True)
if lumped_ethnicities == len(Asian_ethnicities): # if there are no independent Asian ethnicities left
    E_masterDF.rename(index = {'Other Asian' : 'Asian'}, inplace = True)
# repeat for Pacific Islander ethnicities!
lumped_ethnicities = 0
for ethnicity in Pacific_Islander_ethnicities:
    if E_masterDF.at[ethnicity, 'Percent'] < 2: # will group this ethnicity with 'Other Pacific Islander'
        lumped_ethnicities += 1
        E_masterDF.at['Other Pacific Islander', 'Total Count'] += E_masterDF.at[ethnicity, 'Total Count']
        E_masterDF.at['Other Pacific Islander', 'Percent'] += E_masterDF.at[ethnicity, 'Percent']
        for year in CLASSES:
            if E_masterDF.at[ethnicity, year] > 0:
                new_GPA = ((E_masterDF.at['Other Pacific Islander', year +' GPA'] * E_masterDF.at['Other Pacific Islander', year] + 
                                E_masterDF.at[ethnicity, year +' GPA'] * E_masterDF.at[ethnicity, year]) / 
                                (E_masterDF.at['Other Pacific Islander', year] + E_masterDF.at[ethnicity, year]))
                E_masterDF.at['Other Pacific Islander', year +' GPA'] = new_GPA
                E_masterDF.at['Other Pacific Islander', year] += E_masterDF.at[ethnicity, year] 
        E_masterDF.drop(ethnicity, inplace = True)
if lumped_ethnicities == len(Asian_ethnicities): # if there are no independent Pacific Islander ethnicities left
    E_masterDF.rename(index = {'Other Pacific Islander' : 'Pacific Islander'}, inplace = True)
# now doing normal consolidation
consolidate_dataframe(E_masterDF, 'aethnicity')
add_totals_row(E_masterDF)
add_avgGPA_column(E_masterDF)
E_masterDF = format_data(E_masterDF)
print(E_masterDF)


# now to create zip codes dataframe!
Z_masterDF = create_master_dataframe(zip_codes, 'azipcode')
consolidate_dataframe(Z_masterDF, 'azipcode')
add_totals_row(Z_masterDF)
add_avgGPA_column(Z_masterDF)
Z_masterDF = format_data(Z_masterDF)
print(Z_masterDF)

# creating language fluency dataframe
L_masterDF = create_master_dataframe(lang_fluencies, 'langflu')
add_totals_row(L_masterDF)
add_avgGPA_column(L_masterDF)
L_masterDF = format_data(L_masterDF)
print(L_masterDF)

# creating SPED dataframe
# blank SPED field means 'Not SPED'
S_masterDF = create_master_dataframe(sped, 'sped')
if '' in S_masterDF.index:
    S_masterDF.rename(index = {'' : 'Not SPED'}, inplace = True)
    sped.append('Not SPED')
add_totals_row(S_masterDF)
add_avgGPA_column(S_masterDF)
S_masterDF = format_data(S_masterDF)
print(S_masterDF)

# creating cohorts dataframe
C_masterDF = create_master_dataframe(cohorts, 'cohort')
add_totals_row(C_masterDF)
add_avgGPA_column(C_masterDF)
C_masterDF = format_data(C_masterDF)
print(C_masterDF)


# finalized dataframes: G_masterDF, E_masterDF, Z_masterDF, L_masterDF, S_masterDF, C_masterDF

##################################### MAKING SCHOOLWIDE CHARTS ############################################

folder_name = safe_mkdir('./app/static/' + SEMESTER + '/Schoolwide')

# ------------------------ SCHOOLWIDE GENDER CHARTS ------------------------

# bar chart showing gender breakdown of each class
# dataframe: indexes are freshman, sophomore, junior, senior, columns are male, female, nonbinary
SW_genderDF = G_masterDF.loc[genders, CLASSES].transpose()
SW_genderChart = SW_genderDF.plot.bar(rot = 0, title = 'Gender Breakdown by Class').legend(gender_words, loc='center left', bbox_to_anchor=(1.0, 0.5))
pylab.ylabel('Number of students')
#SW_genderChart = SW_genderDF.plot.bar(rot = 0, ylabel = 'Number of students', title = 'Gender Breakdown by Class').legend(gender_words, loc='center left', bbox_to_anchor=(1.0, 0.5))
SW_genderChart.get_figure().savefig(folder_name +'/genderCount.png', bbox_inches = 'tight')
render_mpl_table(G_masterDF.loc[genders, CLASSES], row_labels = gender_words).savefig(folder_name +'/genderCountTable.png')

# bar chart showing avg GPA by gender by class
# dataframe: indexes are classes + avg, columns are male, female, nonbinary
# can maybe pre-make this dictionary?
GPA_by_gender = {}
for gender in genders:
    GPA_by_gender[gender] = G_masterDF.loc[gender, 'Freshman GPA' : 'Class Avg GPA'].tolist()
SW_GPAgenderDF = pd.DataFrame(data = GPA_by_gender, index = CLASSES + ['All Classes'])
SW_GPAgenderChart = SW_GPAgenderDF.plot.bar(rot = 0, title = 'GPA by Gender and Class').legend(gender_words, loc='center left', bbox_to_anchor=(1.0, 0.5))
# SW_GPAgenderChart = SW_GPAgenderDF.plot.bar(rot = 0, ylabel = 'Average GPA', title = 'GPA by Gender and Class').legend(gender_words, loc='center left', bbox_to_anchor=(1.0, 0.5))
pylab.ylabel('Average GPA')
SW_GPAgenderChart.get_figure().savefig(folder_name +'/genderGPA.png', bbox_inches = 'tight')
render_mpl_table(G_masterDF.loc[genders, 'Freshman GPA' : 'Class Avg GPA'], row_labels = gender_words).savefig(folder_name +'/genderGPATable.png')


# ------------------------- SCHOOLWIDE ETHNICITY CHARTS --------------------------------

# pie chart showing ethnicities of entire student body
# might need to be intentional about colors here
SW_ethnicityChart = E_masterDF.loc[E_masterDF.index != 'All', :].plot.pie(y = 'Percent', legend = False, autopct='%.2f', 
                                                                            pctdistance = 0.8, colors = COLORS, figsize = (6, 6)) 
#SW_ethnicityChart = E_masterDF.loc[E_masterDF.index != 'All', :].plot.pie(y = 'Percent', legend = False, ylabel = '', autopct='%.2f', pctdistance = 0.8, colors = COLORS, figsize = (6, 6)) 
SW_ethnicityChart.set_title('Racial/Ethnic Breakdown (%)')
SW_ethnicityChart.get_figure().savefig(folder_name +'/ethnicityCount.png', bbox_inches = 'tight')
render_mpl_table(E_masterDF.loc[E_masterDF.index != 'All', CLASSES + ['Total Count']]).savefig(folder_name +'/ethnicityCountTable.png', bbox_inches = 'tight')

# schoolwide GPA by ethnicity and class bar chart
SW_GPAethnicityChart = E_masterDF.loc[:, 'Freshman GPA' : 'Class Avg GPA'].plot.bar(rot = 80, color = COLORS, width = 0.8, title = 'GPA by Ethnicity and Class').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
SW_GPAethnicityChart = E_masterDF.loc[:, 'Freshman GPA' : 'Class Avg GPA'].plot.bar(rot = 80, color = COLORS, width = 0.8, title = 'GPA by Ethnicity and Class').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
pylab.ylabel('GPA')
#SW_GPAethnicityChart = E_masterDF.loc[:, 'Freshman GPA' : 'Class Avg GPA'].plot.bar(rot = 80, ylabel = 'GPA', color = COLORS, width = 0.8, title = 'GPA by Ethnicity and Class').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
SW_GPAethnicityChart.get_figure().savefig(folder_name +'/ethnicityGPA.png', bbox_inches = 'tight')
render_mpl_table(E_masterDF.loc[E_masterDF.index != 'All', 'Freshman GPA' : 'Class Avg GPA']).savefig(folder_name +'/ethnicityGPATable.png', bbox_inches = 'tight')


# ------------------------- SCHOOLWIDE ZIPCODE CHARTS --------------------------------

# bar chart showing number of students in each zip code
# in dataframe: zip codes are indexes, columns are counts
SW_zipcodeChart = Z_masterDF.loc[Z_masterDF.index != 'All', CLASSES].plot.bar(rot = 65, color = COLORS[2:], width = 0.6, title = 'Zipcode Breakdown').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
pylab.ylabel('Number of Students')
#SW_zipcodeChart = Z_masterDF.loc[Z_masterDF.index != 'All', CLASSES].plot.bar(rot = 65, ylabel = 'Number of Students', color = COLORS[2:], width = 0.6, title = 'Zipcode Breakdown').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
SW_zipcodeChart.get_figure().savefig(folder_name +'/zipcodeCount.png', bbox_inches = 'tight')
render_mpl_table(Z_masterDF.loc[:, CLASSES]).savefig(folder_name +'/zipcodeCountTable.png', bbox_inches = 'tight')

# bar chart showing GPAs of students in each zip code
# in dataframe: zip codes are indexes, columns are GPAs
SW_GPAzipcodeChart = Z_masterDF.loc[:, 'Freshman GPA' : 'Class Avg GPA'].plot.bar(rot = 80, color = COLORS[2:], width = 0.6, title = 'GPA by Zipcode and Class').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
pylab.ylabel('GPA')
#SW_GPAzipcodeChart = Z_masterDF.loc[:, 'Freshman GPA' : 'Class Avg GPA'].plot.bar(rot = 80, ylabel = 'GPA', color = COLORS[2:], width = 0.6, title = 'GPA by Zipcode and Class').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
SW_GPAzipcodeChart.get_figure().savefig(folder_name +'/zipcodeGPA.png', bbox_inches = 'tight')
render_mpl_table(Z_masterDF.loc[:, 'Freshman GPA' : 'Class Avg GPA']).savefig(folder_name +'/zipcodeGPATable.png', bbox_inches = 'tight')

# ------------------------- SCHOOLWIDE ELL & SPED TABLES --------------------------------

# ELL - don't really need any class-specific data in this one, just the total count, percent, and class avg gpa
render_mpl_table(L_masterDF.loc[L_masterDF.index != 'All', ['Total Count', 'Percent', 'Class Avg GPA']]).savefig(folder_name +'/langfluTable.png', bbox_inches = 'tight')
# SPED = same deal!
render_mpl_table(S_masterDF.loc[S_masterDF.index != 'All', ['Total Count', 'Percent', 'Class Avg GPA']]).savefig(folder_name +'/spedTable.png', bbox_inches = 'tight')


# closing figures
matplotlib.pyplot.close('all')



################################## CREATING COHORT CHARTS ######################################

pct = '%'   # because it's an operator in python so strings get weird!

for cohort in cohorts_for_charts:
    # cohort = 'Computer Academy'
    folder_name = safe_mkdir('./app/static/' + SEMESTER + '/' + cohort)
    # getting shortened version of cohort for charts & tables
    if cohort == 'Fashion, Art, and Design Academy':
        cohort_short = 'FADA'
    elif cohort == 'Race, Policy, and Law Academy':
        cohort_short = 'RPL Academy'
    else:
        cohort_short = cohort

    # ----------------------- COHORT GENDER CHARTS --------------------------

    # stacked bar chart showing gender breakdown of cohort vs school
    # in dataframe: indexes are cohort/schoolwide, columns are genders, values are percentages
    school_list = list(G_masterDF.loc[genders, 'Percent'])
    cohort_list = []
    for gender in genders:
        cohort_count = db.user.count_documents({ '$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'agender' : gender}, {'grade' : {'$lte' : 12}}, {'cohort' : cohort} ]})
        cohort_list.append(calculate_percent(cohort_count, C_masterDF.at[cohort, 'Total Count']))
    C_genderDF = pd.DataFrame([cohort_list, school_list], index = [cohort, 'Schoolwide'], columns = gender_words)
    C_genderChart = C_genderDF.plot.bar(rot = 0, stacked = True, color = ['#FFE12D', '#4DFFDA', '#230EF1'], title = 'Gender Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    pylab.ylabel('Percent of total (%)')
    #C_genderChart = C_genderDF.plot.bar(rot = 0, stacked = True, ylabel = 'Percent of total (%)', color = ['#FFE12D', '#4DFFDA', '#230EF1'], title = 'Gender Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    C_genderChart.get_figure().savefig(folder_name +'/genderCount.png', bbox_inches = 'tight')
    C_genderDF = C_genderDF.round(2)
    render_mpl_table(C_genderDF.transpose(), col_labels = [pct+' of '+cohort_short, '% Schoolwide'], col_width = 3.8).savefig(folder_name +'/genderCountTable.png', bbox_inches = 'tight')

    # bar chart showing average GPA by class, gender, and cohort vs schoolwide
    # in dataframe: indexes are classes (excluding freshman) and all, columns are gender x cohort - will fill by columns
    if cohort not in houses:  # this is unneccessary if we're separating houses from other cohorts_for_charts 
        GPA_by_gender = {}
        for gender, gender_word in zip(genders, gender_words):
            if gender == 'N' and db.user.count_documents({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'agender' : 'N'}, {'cohort' : cohort} ]}) == 0:
                continue
            # create column for male compsci, then male schoolwide
            cohort_GPAs = []
            sophomores = db.user.find({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'agender' : gender}, {'cohort' : cohort}, {'grade' : 10}, {'gpa' : { '$exists' : True}} ]}, {'_id': False, 'gpa': True})
            cohort_GPAs.append(average_GPA(sophomores))
            juniors = db.user.find({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'agender' : gender}, {'cohort' : cohort}, {'grade' : 11}, {'gpa' : { '$exists' : True}} ]}, {'_id': False, 'gpa': True})
            cohort_GPAs.append(average_GPA(juniors))
            seniors = db.user.find({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'agender' : gender}, {'cohort' : cohort}, {'grade' : 12}, {'gpa' : { '$exists' : True}} ]}, {'_id': False, 'gpa': True})
            cohort_GPAs.append(average_GPA(seniors))
            all_classes = db.user.find({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'agender' : gender}, {'cohort' : cohort}, {'gpa' : { '$exists' : True}} ]}, {'_id': False, 'gpa': True})
            cohort_GPAs.append(average_GPA(all_classes))
            GPA_by_gender[gender_word + ' ' + cohort_short + ' GPA'] = cohort_GPAs
            GPA_by_gender[gender_word + ' Schoolwide GPA'] = list(G_masterDF.loc[gender, 'Sophomore GPA' :])
        C_GPAgenderDF = pd.DataFrame(data = GPA_by_gender, index = CLASSES[1:] + ['All'])
        C_GPAgenderChart = C_GPAgenderDF.plot.bar(rot = 0, color = COLORS, width = 0.8, title = 'GPA by Gender and Class').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
        pylab.ylabel('Average GPA')
        #C_GPAgenderChart = C_GPAgenderDF.plot.bar(rot = 0, ylabel = 'Average GPA', color = COLORS, width = 0.8, title = 'GPA by Gender and Class').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
        C_GPAgenderChart.get_figure().savefig(folder_name +'/genderGPA.png', bbox_inches = 'tight')
        C_GPAgenderDF = C_GPAgenderDF.round(2)
        render_mpl_table(C_GPAgenderDF, col_width = 4.7).savefig(folder_name +'/genderGPATable.png', bbox_inches = 'tight')

    # ------------------------------ COHORT ETHNICITY CHARTS ---------------------------------


    # stacked bar chart showing ethnic breakdown of cohort vs school
    # in dataframe: indexes are cohort/schoolwide, columns are ethnicities, values are percentages
    school_list = list(E_masterDF.loc[E_masterDF.index != 'All', 'Percent'])
    cohort_list = []
    other_count = 0
    for ethnicity in ethnicities + ['']:
        cohort_count = db.user.count_documents({ '$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'aethnicity' : ethnicity}, {'grade' : {'$lte' : 12}}, {'cohort' : cohort} ]})
        if ethnicity in E_masterDF.index:
            cohort_list.append(calculate_percent(cohort_count, C_masterDF.at[cohort, 'Total Count']))
        else:
            other_count += cohort_count
    cohort_list.append(calculate_percent(other_count, C_masterDF.at[cohort, 'Total Count']))
    C_ethnicityDF = pd.DataFrame([cohort_list, school_list], index = [cohort, 'Schoolwide'], columns = list(E_masterDF.index)[:-1])
    C_ethnicityChart = C_ethnicityDF.plot.bar(rot = 0, stacked = True, color = COLORS, title = 'Racial/Ethnic Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    pylab.ylabel('Percent of total (%)')
    #C_ethnicityChart = C_ethnicityDF.plot.bar(rot = 0, stacked = True, ylabel = 'Percent of total (%)', color = COLORS, title = 'Racial/Ethnic Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    C_ethnicityChart.get_figure().savefig(folder_name +'/ethnicityCount.png', bbox_inches = 'tight')
    C_ethnicityDF = C_ethnicityDF.round(2)
    render_mpl_table(C_ethnicityDF.transpose(), col_labels = [pct+' of '+cohort_short, '% Schoolwide'], col_width = 3.8).savefig(folder_name +'/ethnicityCountTable.png', bbox_inches = 'tight')

    # bar chart showing average GPAs by ethnicity and cohort vs schoolwide
    # dataframe: indexes are ethnicities, columns are cohort/schoolwide, values are avg GPAs
    GPA_by_ethnicity = {}
    cohort_GPAs = []
    others = []
    for ethnicity in ethnicities + ['']:
        students = db.user.find({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'aethnicity' : ethnicity}, {'cohort' : cohort}, {'grade' : {'$lte' : 12}}, {'gpa' : { '$exists' : True}} ]}, {'_id': False, 'gpa': True})
        if ethnicity in E_masterDF.index:
            cohort_GPAs.append(average_GPA(students))
        else:
            others.append(students)
    # need to find avg gpa for ALL groups in one - is there a way to combine cursors? I think I can use itertools and chain them!
    cohort_GPAs.append(average_GPA(chain.from_iterable(others)))
    GPA_by_ethnicity[cohort_short + ' GPA'] = cohort_GPAs
    GPA_by_ethnicity['Schoolwide GPA'] = list(E_masterDF.loc[E_masterDF.index != 'All', 'Class Avg GPA'])
    C_GPAethnicityDF = pd.DataFrame(data = GPA_by_ethnicity, index = list(E_masterDF.index)[:-1])
    C_GPAethnicityChart = C_GPAethnicityDF.plot.bar(rot = 80, color = COLORS, title = 'GPA by Ethnicity').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    pylab.ylabel('Average GPA')
    #C_GPAethnicityChart = C_GPAethnicityDF.plot.bar(rot = 80, ylabel = 'Average GPA', color = COLORS, title = 'GPA by Ethnicity').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    C_GPAethnicityChart.get_figure().savefig(folder_name +'/ethnicityGPA.png', bbox_inches = 'tight')
    C_GPAethnicityDF = C_GPAethnicityDF.round(2)
    render_mpl_table(C_GPAethnicityDF, col_width = 3.8).savefig(folder_name +'/ethnicityGPATable.png', bbox_inches = 'tight')


    # --------------------------- COHORT ZIPCODE CHARTS ----------------------------------


    # bar chart showing zipcode percentage breakdown cohort/schoolwide
    # in dataframe: zip codes are indexes, columns are cohort/schoolwide, values are percentages

    zipcode_breakdowns = {}
    cohort_list = []
    other_count = 0
    for zipcode in zip_codes + ['']:
        cohort_count = db.user.count_documents({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'azipcode' : zipcode}, {'grade' : {'$lte' : 12}}, {'cohort' : cohort} ]})
        if zipcode in Z_masterDF.index:
            cohort_list.append(calculate_percent(cohort_count, C_masterDF.at[cohort, 'Total Count']))
        else:
            other_count += cohort_count
    cohort_list.append(calculate_percent(other_count, C_masterDF.at[cohort, 'Total Count']))
    zipcode_breakdowns[cohort] = cohort_list
    zipcode_breakdowns['Schoolwide'] = list(Z_masterDF.loc[Z_masterDF.index != 'All', 'Percent'])
    C_zipcodeDF = pd.DataFrame(data = zipcode_breakdowns, index = list(Z_masterDF.index)[:-1])
    C_zipcodeChart = C_zipcodeDF.plot.bar(rot = 80, color = COLORS, title = 'Zipcode Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    pylab.ylabel('Percent of Total (%)')
    #C_zipcodeChart = C_zipcodeDF.plot.bar(rot = 80, ylabel = 'Percent of Total (%)', color = COLORS, title = 'Zipcode Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    C_zipcodeChart.get_figure().savefig(folder_name +'/zipcodeCount.png', bbox_inches = 'tight') 
    C_zipcodeDF = C_zipcodeDF.round(2)
    render_mpl_table(C_zipcodeDF, col_width = 3.8, col_labels = [pct+' of '+cohort_short, '% Schoolwide']).savefig(folder_name +'/zipcodeCountTable.png', bbox_inches = 'tight')


    # --------------------------- COHORT SPED & ELL TABLES ----------------------------------

    # need to make a dataframe! indexes are ELL and SPED, columns are cohort/schoolwide, values are percentages


    langflu_list = [
        calculate_percent(db.user.count_documents({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'langflu' : {'$ne' : 'English Only'}}, {'cohort' : cohort}, {'grade' : {'$lte' : 12}} ]}), C_masterDF.at[cohort, 'Total Count']),
        100 - L_masterDF.at['English Only', 'Percent']
    ]
    sped_list = [
        calculate_percent(db.user.count_documents({'$and' : [{'role' : {'$in' : ['Student', 'student']}}, {'sped' : {'$ne' : ''}}, {'cohort' : cohort}, {'grade' : {'$lte' : 12}} ]}), C_masterDF.at[cohort, 'Total Count']),
        100 - S_masterDF.at['Not SPED', 'Percent']
    ]
    C_spedEllDF = pd.DataFrame(data = [langflu_list, sped_list], index = ['ELL', 'SPED'], columns = [pct+' of '+ cohort_short, '% Schoolwide']).round(2)
    render_mpl_table(C_spedEllDF, col_width = 3.8).savefig(folder_name +'/spedEllTable.png', bbox_inches = 'tight')


    # closing all figures after each cohort
    matplotlib.pyplot.close('all')







################      Charts for 9th grade       ###################
# for these charts, 'cohort' means 9th graders

cohort = '9th Grade'

folder_name = safe_mkdir('./app/static/' + SEMESTER + '/9th Grade')

have_GPAs = True
if C_masterDF.at['All', 'Freshman GPA'] == 0:
    have_GPAs = False

# ----------------------- GENDER CHARTS --------------------------

# stacked bar chart showing gender breakdown of cohort vs school
# in dataframe: indexes are cohort/schoolwide, columns are genders, values are percentages
school_list = list(G_masterDF.loc[genders, 'Percent'])
cohort_list = []
for num in list(G_masterDF.loc[genders, 'Freshman']):
    cohort_list.append(calculate_percent(num, C_masterDF.at['All', 'Freshman']))
F_genderDF = pd.DataFrame([cohort_list, school_list], index = [cohort, 'Schoolwide'], columns = gender_words)
F_genderChart = F_genderDF.plot.bar(rot = 0, stacked = True, color = ['#FFE12D', '#4DFFDA', '#230EF1'], title = 'Gender Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
pylab.ylabel('Percent of Total (%)')
#F_genderChart = F_genderDF.plot.bar(rot = 0, stacked = True, ylabel = 'Percent of total (%)', color = ['#FFE12D', '#4DFFDA', '#230EF1'], title = 'Gender Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
F_genderChart.get_figure().savefig(folder_name +'/genderCount.png', bbox_inches = 'tight')
F_genderDF = F_genderDF.round(2)
render_mpl_table(F_genderDF.transpose(), col_labels = [pct+' of '+cohort, '% Schoolwide'], col_width = 3.8).savefig(folder_name +'/genderCountTable.png', bbox_inches = 'tight')

# bar chart showing average GPA by gender, and cohort vs schoolwide
# in dataframe: indexes are genders, columns are cohort/schoolwide, values are GPAs
if have_GPAs:
    F_GPAgenderDF = pd.DataFrame(data = {'9th Grade' : list(G_masterDF.loc[genders, 'Freshman GPA']), 'Schoolwide' : list(G_masterDF.loc[genders, 'Class Avg GPA'])}, index = gender_words)
    F_GPAgenderChart = F_GPAgenderDF.plot.bar(rot = 0, color = COLORS, width = 0.8, title = 'GPA by Gender').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    pylab.ylabel('Average GPA')
    #F_GPAgenderChart = F_GPAgenderDF.plot.bar(rot = 0, ylabel = 'Average GPA', color = COLORS, width = 0.8, title = 'GPA by Gender').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    F_GPAgenderChart.get_figure().savefig(folder_name +'/genderGPA.png', bbox_inches = 'tight')
    F_GPAgenderDF = F_GPAgenderDF.round(2)
    render_mpl_table(F_GPAgenderDF, col_width = 4.7).savefig(folder_name +'/genderGPATable.png', bbox_inches = 'tight')


# ----------------------- ETHNICITY CHARTS --------------------------


# stacked bar chart showing ethnic breakdown of cohort vs school
# in dataframe: indexes are cohort/schoolwide, columns are ethnicities, values are percentages
school_list = list(E_masterDF.loc[E_masterDF.index != 'All', 'Percent'])
cohort_list = []
for num in list(E_masterDF.loc[E_masterDF.index != 'All', 'Freshman']):
    cohort_list.append(calculate_percent(num, C_masterDF.at['All', 'Freshman']))
F_ethnicityDF = pd.DataFrame([cohort_list, school_list], index = [cohort, 'Schoolwide'], columns = list(E_masterDF.index)[:-1])
F_ethnicityChart = F_ethnicityDF.plot.bar(rot = 0, stacked = True, color = COLORS, title = 'Racial/Ethnic Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
#F_ethnicityChart = F_ethnicityDF.plot.bar(rot = 0, stacked = True, ylabel = 'Percent of total (%)', color = COLORS, title = 'Racial/Ethnic Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
F_ethnicityChart.get_figure().savefig(folder_name +'/ethnicityCount.png', bbox_inches = 'tight')
F_ethnicityDF = F_ethnicityDF.round(2)
render_mpl_table(F_ethnicityDF.transpose(), col_labels = [pct+' of '+cohort, '% Schoolwide'], col_width = 3.8).savefig(folder_name +'/ethnicityCountTable.png', bbox_inches = 'tight')


# bar chart showing average GPAs by ethnicity and cohort vs schoolwide
# dataframe: indexes are ethnicities, columns are cohort/schoolwide, values are avg GPAs
if have_GPAs:
    F_GPAethnicityDF = pd.DataFrame(data = {'9th Grade' : E_masterDF.loc[E_masterDF.index != 'All', 'Freshmen GPA'], 'Schoolwide' : E_masterDF.loc[E_masterDF.index != 'All', 'Class Avg GPA']}, index = list(E_masterDF.index)[:-1])
    F_GPAethnicityChart = F_GPAethnicityDF.plot.bar(rot = 80, color = COLORS, title = 'GPA by Ethnicity').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    pylab.ylabel('Average GPA')
    #F_GPAethnicityChart = F_GPAethnicityDF.plot.bar(rot = 80, ylabel = 'Average GPA', color = COLORS, title = 'GPA by Ethnicity').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
    F_GPAethnicityChart.get_figure().savefig(folder_name +'/ethnicityGPA.png', bbox_inches = 'tight')
    F_GPAethnicityDF = F_GPAethnicityDF.round(2)
    render_mpl_table(F_GPAethnicityDF, col_width = 3.8).savefig(folder_name +'/ethnicityGPATable.png', bbox_inches = 'tight')


# ----------------------- ZIPCODE CHARTS --------------------------

# bar chart showing zipcode percentage breakdown cohort/schoolwide
# in dataframe: zip codes are indexes, columns are cohort/schoolwide, values are percentages
school_list = list(Z_masterDF.loc[Z_masterDF.index != 'All', 'Percent'])
cohort_list = []
for num in list(Z_masterDF.loc[Z_masterDF.index != 'All', 'Freshman']):
    cohort_list.append(calculate_percent(num, C_masterDF.at['All', 'Freshman']))
F_zipcodeDF = pd.DataFrame(data = {'9th Grade' : cohort_list, 'Schoolwide' : school_list}, index = list(Z_masterDF.index)[:-1])
F_zipcodeChart = F_zipcodeDF.plot.bar(rot = 80, color = COLORS, title = 'Zipcode Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
pylab.ylabel('Percent of Total (%)')
#F_zipcodeChart = F_zipcodeDF.plot.bar(rot = 80, ylabel = 'Percent of total (%)', color = COLORS, title = 'Zipcode Breakdowns').legend(loc='center left',bbox_to_anchor=(1.0, 0.5))
F_zipcodeChart.get_figure().savefig(folder_name +'/zipcodeCount.png', bbox_inches = 'tight')
F_zipcodeDF = F_zipcodeDF.round(2)
render_mpl_table(F_zipcodeDF, col_labels = [pct+' of '+cohort, '% Schoolwide'], col_width = 3.8).savefig(folder_name +'/zipcodeCountTable.png', bbox_inches = 'tight')


# ----------------------- SPED & ELL TABLES --------------------------


# need to make a dataframe! indexes are ELL and SPED, columns are cohort/schoolwide, values are percentages


langflu_list = [
    calculate_percent(L_masterDF.at['All', 'Freshman'] - L_masterDF.at['English Only', 'Freshman'], C_masterDF.at['All', 'Freshman']),
    100 - L_masterDF.at['English Only', 'Percent']
]
sped_list = [
    calculate_percent(S_masterDF.at['All', 'Freshman'] - S_masterDF.at['Not SPED', 'Freshman'], C_masterDF.at['All', 'Freshman']),
    100 - S_masterDF.at['Not SPED', 'Percent']
]
F_spedEllDF = pd.DataFrame(data = [langflu_list, sped_list], index = ['ELL', 'SPED'], columns = [pct+' of '+ cohort, '% Schoolwide']).round(2)
render_mpl_table(F_spedEllDF, col_width = 3.8).savefig(folder_name +'/spedEllTable.png', bbox_inches = 'tight')

cohorts_for_charts.append('9th Grade')