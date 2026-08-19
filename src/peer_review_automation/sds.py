#!/usr/bin/env python3

import os

import pandas as pd
import xlsxwriter


class SDSData():
    def __init__(self,nameCheck, SDS_file_path = None, val_file_path = None):    
        if SDS_file_path is None:
            print("No file selected!")
            return
        file_name = os.path.split(SDS_file_path)[1]
        self.file_name = file_name.split('-')[0]
        self.SDSAllData = pd.read_excel(SDS_file_path, sheet_name=["Form Definitions", "Codelists"])   
        self.errorList = []
        #self.df = pd.DataFrame(self.FDdata, columns= ['Form Name','Item Name', 'External ID', 'Label'])
        self.df = self.SDSAllData['Form Definitions']
        self.df1 = self.SDSAllData['Codelists']
        self.APR(nameCheck)
        self.val_file_path = val_file_path
        if val_file_path is not None:
            self.validation(val_file_path)
        
    def validation(self, val_file_path):
        self.val_df = pd.read_csv(val_file_path)
        self.val_df = self.val_df[['Category', 'Section', 'Error Name', 'Description','Object']]
        to_remove = ['Item Group Tabular Display Contains Label', 'Multiple dynamic rules on object', 'Item length is longer than the longest codelist item', 'Hide/Show in Editable Grid','Rule evaluation might result in too many permutations']
        self.val_df = self.val_df[~self.val_df['Error Name'].astype(str).str.contains('|'.join(to_remove))]
        self.val_df = self.val_df.drop_duplicates()
        

    def APR(self, nameCheck = False):
        df = self.df
        df1 = self.df1
        for i in range(len(df)):
            # check Item
            ## check if it's item name not null
            if not pd.isnull(df.loc[i, "Item Name"]):
                
                # check length of item name if > 32 char
                if len(df.loc[i, "Item Name"]) > 32:
                    self.errorList.append([df.loc[i, "Form Label"],
                                           df.loc[i, "Item Group Label"],
                                           df.loc[i, "Label"],
                                           "Item Name Length",
                                           df.loc[i, "Item Name"] + " has length of {} characters".format(str(len(df.loc[i, "Item Name"])))])

                # check if field is required
                if df.loc[i, "Required"] == 'No' and df.loc[i, "Data Type"] != 'Label' and df.loc[i, "Data Type"] != 'Boolean':
                    self.errorList.append([df.loc[i, "Form Label"],
                                           df.loc[i, "Item Group Label"],
                                           df.loc[i, "Label"],
                                           "Not Required",
                                           "Field should be required"])

                # check if date field No Future Date is selected
                if df.loc[i, "Data Type"]  == "Date" and df.loc[i, "No Future Date"] != "Yes":
                    self.errorList.append([df.loc[i, "Form Label"],
                                           df.loc[i, "Item Group Label"],
                                           df.loc[i, "Label"],
                                           "Date Field - No Future Date",
                                           "Date Field No Future Date needs to be selected"])

                # check match external ID
                if df.loc[i, "Item Name"]  != df.loc[i, "External ID"]:
                    self.errorList.append([df.loc[i, "Form Label"],
                                           df.loc[i, "Item Group Label"],
                                           df.loc[i, "Label"],
                                           "Item Name and External ID not matching", 
                                           "Item Name:" +  df.loc[i, "Item Name"] + " | " + "External ID:" + df.loc[i, "External ID"]])
                
                if df.loc[i, "Data Type"] == "Codelist":
                # check display of codelist
                    count_options = len(df1[(df1['Name'].str.contains(df.loc[i, "Codelist"] + '$', na=False)) & (df1['Hidden'] == False)])  # noqa: E712
                    # print(str(df.loc[i, "Form Label"]) + str(df.loc[i, "Label"]) + " Codelist display type is picklist " + df.loc[i, "Codelist"] +  str(count_options))
                    if (count_options == 1 or count_options == 2) and df.loc[i, "Control Type"] == "Picklist":
                        self.errorList.append([df.loc[i, "Form Label"],
                                               df.loc[i, "Item Group Label"],
                                               df.loc[i, "Label"],
                                               "Codelist display type is picklist", 
                                               "Item name: " +  df.loc[i, "Item Name"] + " | " + df.loc[i, "Codelist"] + " with display type of {} but has {} options".format(df.loc[i, "Control Type"], count_options)])
                    
                    elif (count_options > 2) and df.loc[i, "Control Type"] != "Picklist":
                        self.errorList.append([df.loc[i, "Form Label"],
                                               df.loc[i, "Item Group Label"],
                                               df.loc[i, "Label"],
                                               "Codelist display type is not picklist", 
                                               "Item name: " +  df.loc[i, "Item Name"] + " | " + df.loc[i, "Codelist"] + " with display type of {} but has {} options".format(df.loc[i, "Control Type"], count_options)])
                if nameCheck:
                    self.itemNameCheck(i)

            ## check if item name is null but Item Group Name is not null
            if pd.isnull(df.loc[i, "Item Name"]) and not pd.isnull(df.loc[i, "Item Group Name"]):

                # check match external ID
                if df.loc[i, "Item Group Name"]  != df.loc[i, "External ID"]:
                    self.errorList.append([df.loc[i, "Form Label"],
                                           df.loc[i, "Item Group Label"],
                                           "n/a",
                                           "Item Group Name and External ID mismatch", 
                                           "Item Group Name: " +  df.loc[i, "Item Group Name"] + " | " + "External ID:" + df.loc[i, "External ID"]])

                if df.loc[i, "Visual Group"] != "Yes":
                    self.errorList.append([df.loc[i, "Form Label"],
                                           df.loc[i, "Item Group Label"],
                                           "n/a",
                                           "Item Group does not have Visual Group selected Yes", 
                                           "Item Group Name: " +  df.loc[i, "Item Group Name"]  + " Visual Group should be Yes"])
                    
                if df.loc[i, "Header Visible"] != "Yes":
                    self.errorList.append([df.loc[i, "Form Label"],
                                           df.loc[i, "Item Group Label"],
                                           "n/a",
                                           "Item Group does not have Header Visible selected Yes", 
                                           "Item Group Name: " +  df.loc[i, "Item Group Name"]  + " Header Visible should be Yes"])

                if nameCheck:
                    self.itemGroupNameCheck(i)
        # print(*self.errorList,sep='\n')
        

    def itemNameCheck(self, i):
        df = self.df
        #check type of field
        if df.loc[i, "Data Type"] == "Codelist" and df.loc[i, "Item Name"][0:3] != "CL_":
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   df.loc[i, "Label"],
                                   "Wrong Item Name for Codelist Item",
                                   "Item Name:" +  df.loc[i, "Item Name"] + " doesn't have CL_ as the first three character"])
        elif df.loc[i, "Data Type"] == "Date":
            if (df.loc[i, "Item Name"][0:3] != "DT_" and pd.isnull(df.loc[i, "Mask"])):
                self.errorList.append([df.loc[i, "Form Label"],
                                       df.loc[i, "Item Group Label"],
                                       df.loc[i, "Label"], 
                                       "Wrong Item Name for Date Item", 
                                       "Item Name:" +  df.loc[i, "Item Name"] + " doesn't have DT_ as the first three character"])
            elif (df.loc[i, "Item Name"][0:3] != "PD_" and not pd.isnull(df.loc[i, "Mask"])):
                self.errorList.append([df.loc[i, "Form Label"],
                                       df.loc[i, "Item Group Label"],
                                       df.loc[i, "Label"], 
                                       "Wrong Item Name for Date Item",
                                       "Item Name:" +  df.loc[i, "Item Name"] + " doesn't have PD_ as the first three character"])
        elif df.loc[i, "Data Type"] == "Label" and df.loc[i, "Item Name"][0:3] != "LB_":
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   df.loc[i, "Label"], 
                                   "Wrong Item Name for Label Item",
                                   "Item Name:" +  df.loc[i, "Item Name"] + " doesn't have LB_ as the first three character"])
        elif df.loc[i, "Data Type"] == "Number" and df.loc[i, "Item Name"][0:3] != "NM_":
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   df.loc[i, "Label"], 
                                   "Wrong Item Name for Number Item", 
                                   "Item Name:" +  df.loc[i, "Item Name"] + " doesn't have NM_ as the first three character"])
        elif df.loc[i, "Data Type"] == "Text" and not pd.isnull(df.loc[i, "Derived"]) and df.loc[i, "Item Name"][0:3] != "DV_":
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   df.loc[i, "Label"], 
                                   "Wrong Item Name for Derived Item", 
                                   "Item Name:" +  df.loc[i, "Item Name"] + " doesn't have DV_ as the first three character"])
        elif df.loc[i, "Data Type"] == "Text" and pd.isnull(df.loc[i, "Derived"]) and df.loc[i, "Item Name"][0:3] != "TX_":
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   df.loc[i, "Label"], 
                                   "Wrong Item Name for Text Item", 
                                   "Item Name:" +  df.loc[i, "Item Name"] + " doesn't have TX_ as the first three character"])
        elif df.loc[i, "Data Type"] == "Time" and df.loc[i, "Item Name"][0:3] != "TM_":
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   df.loc[i, "Label"], 
                                   "Wrong Item Name for Time Item", 
                                   "Item Name:" +  df.loc[i, "Item Name"] + " doesn't have TM_ as the first three character"])
        elif df.loc[i, "Data Type"] == "Unit" and df.loc[i, "Item Name"][0:3] != "UN_":
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   df.loc[i, "Label"], 
                                   "Wrong Item Name for Unit Item", 
                                   "Item Name:" +  df.loc[i, "Item Name"] + " doesn't have UN_ as the first three character"])
        # check if codelist item has the same codelist linked to it
        
        if df.loc[i, "Data Type"] == "Codelist":
            # index _cl_
            try:
                clIndex = df.loc[i, "Item Name"].rindex("_cl_")
            except ValueError:
                self.errorList.append([df.loc[i, "Form Label"],
                                       df.loc[i, "Item Group Label"],
                                       df.loc[i, "Label"], 
                                       "Item codelist type missing codelist attachment part", 
                                       "Item name: " + df.loc[i, "Item Name"] + " | Codelist: " + df.loc[i, "Codelist"]])
            else:
                # check if codelist match referenced codelist in item name
                if df.loc[i, "Item Name"][clIndex + 1:] != df.loc[i, "Codelist"]:
                    self.errorList.append([df.loc[i, "Form Label"],
                                           df.loc[i, "Item Group Label"],
                                           df.loc[i, "Label"], 
                                           "Codelist item name not matching codelist", 
                                           "Item name: " +  df.loc[i, "Item Name"] + " | " + df.loc[i, "Codelist"]])
                
                #check if codelist is shared or not
                count_cl = len(df[['Item Name','Codelist']].loc[df['Codelist'].str.contains(df.loc[i, "Codelist"] + '$', na=False)].drop_duplicates())
                if count_cl > 1:
                    if "_YS_" not in df.loc[i, 'Codelist']:
                        self.errorList.append([df.loc[i, "Form Label"],
                                           df.loc[i, "Item Group Label"],
                                           df.loc[i, "Label"], 
                                           "Shared codelist named as NS or missing YS",
                                           "Codelist:" +  df.loc[i, "Codelist"] + " is shared {} times".format(count_cl)])
                elif count_cl == 1:
                    if "_NS_" not in df.loc[i, 'Codelist']:
                        self.errorList.append([df.loc[i, "Form Label"],
                                           df.loc[i, "Item Group Label"],
                                           df.loc[i, "Label"], 
                                           "Not shared codelist named as YS or missing NS", 
                                           "Codelist:" +  df.loc[i, "Codelist"] + " is not shared."])

        if df.loc[i, "Data Type"] == "Unit":
            # index _un_
            try:
                clIndex = df.loc[i, "Item Name"].rindex("_un_")
            except ValueError:
                self.errorList.append([df.loc[i, "Form Label"], 
                                       df.loc[i, "Item Group Label"], 
                                       df.loc[i, "Label"], 
                                       "Item Unit type missing Unit Codelist attachment part",
                                       "Item name: " + df.loc[i, "Item Name"] + " | Unit Codelist: " + df.loc[i, "Unit Codelist"]])
            else:
                if df.loc[i, "Item Name"][clIndex + 1:] != df.loc[i, "Unit Codelist"]:
                    self.errorList.append([df.loc[i, "Form Label"],
                                           df.loc[i, "Item Group Label"],
                                           df.loc[i, "Label"],
                                           "Unit item name not matching unit",
                                           "Item name: " +  df.loc[i, "Item Name"] + " | " + df.loc[i, "Unit Codelist"]])

        # check YS/NS
        count_items = len(df.loc[df['Item Name'].str.contains('^' + df.loc[i, "Item Name"] + '$', na=False)])
        if count_items > 1:
            if "_YS_" not in df.loc[i, 'Item Name']:
                self.errorList.append([df.loc[i, "Form Label"],
                                       df.loc[i, "Item Group Label"],
                                       df.loc[i, "Label"],
                                       "Shared item named as NS or missing YS",
                                       "Item Name:" +  df.loc[i, "Item Name"] + " is shared {} times".format(count_items)])
        elif count_items == 1:
            if "_NS_" not in df.loc[i, 'Item Name']:
                self.errorList.append([df.loc[i, "Form Label"],
                                       df.loc[i, "Item Group Label"],
                                       df.loc[i, "Label"],
                                       "Not shared item named as YS or missing NS",
                                       "Item Name:" +  df.loc[i, "Item Name"] + " is not shared"])
        
        
        # check NA for help text label
        if df.loc[i, 'Data Type'] == "Label" and df.loc[i, "Item Name"][6:8] != "NA":
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   df.loc[i, "Label"],
                                   "Wrong Item Name",
                                   "Item Name:" +  df.loc[i, "Item Name"] + " doesn't have NA as the 7th and 8th letters"])
        elif df.loc[i, 'Data Type'] != "Label":
            # check NH
            if "_NH_" in df.loc[i, 'Item Name'] and not pd.isnull(df.loc[i, "Hover Help"]):
                self.errorList.append([df.loc[i, "Form Label"],
                                       df.loc[i, "Item Group Label"],
                                       df.loc[i, "Label"],
                                       "Item with help text named as NH",
                                       "Item Name:" +  df.loc[i, "Item Name"] + " has help text"])
        
            # check YH
            if "_YH_" in df.loc[i, 'Item Name'] and pd.isnull(df.loc[i, "Hover Help"]):
                self.errorList.append([df.loc[i, "Form Label"],
                                       df.loc[i, "Item Group Label"],
                                       df.loc[i, "Label"],
                                       "Item without help text named as YH",
                                       "Item Name:" +  df.loc[i, "Item Name"] + " doesn't have help text"])


        # check HLPLABEL
        if df.loc[i, 'Data Type'] == "Label" and df.loc[i, 'Label Type'] == "Help" and "WIHLPLABEL" not in df.loc[i, 'Item Name']:
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   df.loc[i, "Label"],
                                   "Missing WIHLPLABEL in Field Name",
                                   "Item Name:" +  df.loc[i, "Item Name"] + " is not matching with the label type. Current label type is " + df.loc[i, 'Label Type']])
        
        # check INFLABEL
        if df.loc[i, 'Data Type'] == "Label" and df.loc[i, 'Label Type'] == "Informational" and "INFLABEL" not in df.loc[i, 'Item Name']:
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   df.loc[i, "Label"],
                                   "Missing INFLABEL in Field Name",
                                   "Item Name:" +  df.loc[i, "Item Name"] + " is not matching with the label type. Current label type is " + df.loc[i, 'Label Type']])
        
        # check WARLABEL
        if df.loc[i, 'Data Type'] == "Label" and df.loc[i, 'Label Type'] == "Warning" and "WARLABEL" not in df.loc[i, 'Item Name']:
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   df.loc[i, "Label"],
                                   "Missing WARLABEL in Field Name",
                                   "Item Name:" +  df.loc[i, "Item Name"] + " is not matching with the label type. Current label type is " + df.loc[i, 'Label Type']])

    def itemGroupNameCheck(self, i):

        df = self.df
        #check name: 
        if df.loc[i, "Item Group Name"][0:2] != "IG":
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"], 
                                   "",
                                   "Wrong Item Group Name",
                                   "Item Group Name: " +  df.loc[i, "Item Group Name"] + " doesn't have IG as the first two letter"])
        
        #check YS NS
        count_ig = len(df.loc[(df['Item Group Name'].str.contains('^' + df.loc[i, "Item Group Name"] + '$', na=False)) & (df['Item Name'].isna())])
        if count_ig > 1:
            if "_YS_" not in df.loc[i, 'Item Group Name']:
                self.errorList.append([df.loc[i, "Form Label"],
                                       df.loc[i, "Item Group Label"],
                                       "",
                                       "Shared item group named as NS or missing YS",
                                       "Item Group Name: " +  df.loc[i, "Item Group Name"] + " is shared {} times".format(count_ig)])
        elif count_ig == 1:
            if "_NS_" not in df.loc[i, 'Item Group Name']:
                self.errorList.append([df.loc[i, "Form Label"],
                                       df.loc[i, "Item Group Label"],
                                       "",
                                       "Not shared item group named as YS or missing NS", "Item Group Name: " +  df.loc[i, "Item Group Name"] + " is not shared"])
        
        #check NA
        if df.loc[i, "Item Group Name"][6:8] != "NA":
            self.errorList.append([df.loc[i, "Form Label"],
                                   df.loc[i, "Item Group Label"],
                                   "",
                                   "Wrong Item Group Name",
                                   "Item Group Name: " +  df.loc[i, "Item Group Name"] + " doesn't have NA as the 7th and 8th letters"])
        
    def codelistsCheck(self):
        df1 = self.df1
        for i in range(len(df1)):
            if not pd.isnull(df1.loc[i, "Choice Code"]):
                if df1.loc[i, "Choice Label"] == "Yes" and df1.loc[i, "Choice Code"] != 1:
                    self.errorList.append(["", "", "","Wrong Code for Codelist", "Codelist: " +  df1.loc[i, "Item Group Name"] + " doesn't have NA as the 7th and 8th letters"])
        pass

    def name2Al(self,*args):
        columnLetters = []
        for columnName in args:
            #convert column name to number first
            columnNumber = self.df.columns.get_loc(columnName)
            #convert column number to alphabetical letter
            columnLetter = xlsxwriter.utility.xl_col_to_name(columnNumber)
            columnLetters.append(columnLetter)
        
        return ', '.join(columnLetters)

    def name2Al_2(self,*args):
        columnLetters = []
        for columnName in args:
            #convert column name to number first
            columnNumber = self.df1.columns.get_loc(columnName)
            #convert column number to alphabetical letter
            columnLetter = xlsxwriter.utility.xl_col_to_name(columnNumber)
            columnLetters.append(columnLetter)
        
        return ', '.join(columnLetters)
    
    def output(self, filepath):
        output_df = pd.DataFrame(self.errorList, columns=['Form Label', 'Item Group Label','Item','Type of Error', 'Details'])
        with pd.ExcelWriter(filepath  + '/' + self.file_name + ' Peer Review Automation Output.xlsx') as writer:  
            output_df.to_excel(writer, sheet_name='Form Definition Review', index = False)
            worksheet1 = writer.sheets['Form Definition Review']
            blue_header_format = writer.book.add_format({'bg_color': '#B7DEE8',
                                                                'text_wrap': True,
                                                                'valign': 'vcenter',
                                                                'align': 'center',
                                                                'bold' : True,
                                                                'border': 2})
            for i in range (5):
                worksheet1.write(0, i, output_df.columns.values[i], blue_header_format)
            worksheet1.autofit()
            worksheet1.set_row(0, 40)
            worksheet1.set_column('A:C', 30)
            if self.val_file_path is not None:
                
                self.val_df.to_excel(writer, sheet_name='Validation Review', index = False)
                worksheet2 = writer.sheets['Validation Review']
                blue_header_format = writer.book.add_format({'bg_color': '#B7DEE8',
                                                                    'text_wrap': True,
                                                                    'valign': 'vcenter',
                                                                    'align': 'center',
                                                                    'bold' : True,
                                                                    'border': 2})
                for i in range (5):
                    worksheet2.write(0, i, self.val_df.columns.values[i], blue_header_format)
                worksheet2.autofit()
                worksheet2.set_row(0, 40)
                worksheet2.set_column('A:C', 30)
            
            

