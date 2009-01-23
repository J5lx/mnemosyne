#
# card_appearance_dlg.py <Peter.Bienstman@UGent.be>
#

import gettext
_ = gettext.gettext

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from ui_card_appearance_dlg import Ui_CardAppearanceDlg

from mnemosyne.libmnemosyne.component_manager import config, card_types


class CardAppearanceDlg(QDialog, Ui_CardAppearanceDlg):

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.dynamic_widgets = []
        self.affected_card_types = []
        self.key_names = []
        # We calculate card_type_by_name here rather than in the component
        # manager, because these names can change if the user chooses another
        # translation.
        self.card_types.addItem(_("<all card types>"))
        self.card_type_by_name = {}
        for card_type in card_types():
            self.card_type_by_name[card_type.name] = card_type
            self.card_types.addItem(card_type.name)

    def card_type_changed(self, new_card_type_name):
        if new_card_type_name == _("<all card types>"):
            self.affected_card_types = card_types()
            self.key_names = ["Text"]
        else:
            new_card_type_name = unicode(new_card_type_name)
            new_card_type = self.card_type_by_name[new_card_type_name]
            self.affected_card_types = [new_card_type]
            self.key_names = new_card_type.key_names()

        for widget in self.dynamic_widgets:
            self.gridLayout.removeWidget(widget)
            widget.close()
        self.dynamic_widgets = []

        row = 2
        self.font_buttons = QButtonGroup()
        self.colour_buttons = QButtonGroup()
        self.align_buttons = QButtonGroup()
        for key_name in self.key_names:
            label = QLabel(key_name + ":", self)
            self.gridLayout.addWidget(label, row, 0, 1, 1)
            self.dynamic_widgets.append(label)
            
            font = QPushButton(_("Font"), self)
            self.font_buttons.addButton(font, row-2)
            self.gridLayout.addWidget(font, row, 1, 1, 1)
            self.dynamic_widgets.append(font)
            
            colour = QPushButton(_("Colour"),self)
            self.colour_buttons.addButton(colour, row-2)
            self.gridLayout.addWidget(colour, row, 2, 1, 1)
            self.dynamic_widgets.append(colour)
            
            left_align = QCheckBox(_("Left align"), self)
            self.align_buttons.addButton(left_align, row-2)
            self.gridLayout.addWidget(left_align, row, 3, 1, 1)
            self.dynamic_widgets.append(left_align)
            
            row += 1
            
        self.connect(self.font_buttons, SIGNAL("buttonClicked(int)"),
                     self.update_font)
        self.connect(self.colour_buttons, SIGNAL("buttonClicked(int)"),
                     self.update_colour)
        self.connect(self.align_buttons, SIGNAL("buttonClicked(int)"),
                     self.update_align)
        
    def update_font(self, index):
        # Determine keys affected.
        if len(self.affected_card_types) > 1:
            affected_key = None # Actually means all the keys.
        else:
            affected_key = self.affected_card_types[0].fields[index][0]
            
        # Determine current font.
        current_font = QFont(self.font())
        try:
            if len(self.affected_card_types) > 1:
                font_string = config()['font']['1']['q']
            else:
                font_string = config()['font'][self.affected_card_types[0].id]\
                                                             [affected_key]
            current_font.fromString(font_string)
        except:
            pass
        
        # Set new font.
        font, ok = QFontDialog.getFont(current_font, self)
        if ok:
            font_string = unicode(font.toString())
            for card_type in self.affected_card_types:
                card_type.get_renderer().set_property('font', font_string,
                                                      card_type, affected_key)
        
    def update_colour(self, index):
        # Determine keys affected.
        if len(self.affected_card_types) > 1:
            affected_key = None # Actually means all the keys.
        else:
            affected_key = self.affected_card_types[0].fields[index][0]
            
        # Determine current colour.
        current_colour = Qt.green
        if 1:
            if len(self.affected_card_types) > 1:
                current_rgb = config()['colour']['1']['q']
            else:
                current_rgb = config()['colour']\
                             [self.affected_card_types[0].id][affected_key]
            print current_rgb
            current_colour = QColor(current_rgb)
        else:
            pass
        print current_colour
        
        # Set new colour.
        colour = QColorDialog.getColor(Qt.blue, self)
        if colour.isValid():
            print "%X" % colour.rgb()

            # Note: convert to CSS colour names:
            #colour = "%X" % colour.rgb() # FFrrggbb
            #colour = "#" + colour[2:] # Xrrggbb
            for card_type in self.affected_card_types:
                card_type.get_renderer().set_property('colour', colour.rgb(),
                                                      card_type, affected_key)
        
    def update_align(self, index):
        print 'updated align', index
        
    def update_background_colour(self):
        print 'updated background colour'
        
    def preview(self):
        fact_data = self.card_type.widget.get_data(check_for_required=False)
        fact = Fact(fact_data, self.card_type)
        cards = self.card_type.create_related_cards(fact)
        cat_text = self.categories.currentText()
        if cat_text == _("<default>"):
            cat_text = ""
        dlg = PreviewCardsDlg(cards, cat_text, self)
        dlg.exec_()