from ipywidgets import widgets, Checkbox, FloatSlider, VBox, IntSlider
#from glue_jupyter.widgets import Color, Size

from glue.config import colormaps
from glue.utils import color2hex


import traitlets
from glue_jupyter.state_traitlets_helpers import GlueState
from glue_jupyter.vuetify_helpers import link_glue_choices
from glue_jupyter.link import link, dlink
from glue_jupyter.widgets import LinkedDropdown


__all__ = ['MapLayerStateWidget']

class MapLayerStateWidget(VBox):
    
    def __init__(self, layer_state):
        
        self.state = layer_state
        
        self.widget_visible = Checkbox(description='visible', value=self.state.visible)
        link((self.state, 'visible'), (self.widget_visible, 'value'))
        
        #self.widget_opacity = FloatSlider(min=0, max=1, step=0.01, value=self.state.alpha,
        #                                  description='opacity')
        #link((self.state, 'alpha'), (self.widget_opacity, 'value'))

        
        self.widget_color = Color(state=self.state) 

        
        super().__init__()
        
        self.glue_state = layer_state
        
        link_glue_choices(self, layer_state, 'colormap_att')
        link_glue_choices(self, layer_state, 'colormap_name')
        
class Color(VBox):
        
    def __init__(self, state, **kwargs):
        super(Color, self).__init__(**kwargs)
        self.state = state

        self.widget_color = widgets.ColorPicker(description='color')
        link((self.state, 'color'), (self.widget_color, 'value'), color2hex)

        colormap_mode_options = type(self.state).colormap_mode.get_choice_labels(self.state)
        self.widget_colormap_mode = widgets.RadioButtons(options=colormap_mode_options,
                                                     description='colormap mode')
        link((self.state, 'colormap_mode'), (self.widget_colormap_mode, 'value'))

        self.widget_colormap_att = LinkedDropdown(self.state, 'colormap_att',
                                              ui_name='color attribute',
                                              label='color attribute')

        self.widget_colormap_vmin = widgets.FloatText(description='color min')
        self.widget_colormap_vmax = widgets.FloatText(description='color max')
        self.widget_colormap_v = widgets.VBox([self.widget_colormap_vmin, self.widget_colormap_vmax])
        link((self.state, 'colormap_vmin'), (self.widget_colormap_vmin, 'value'), lambda value: value or 0)
        link((self.state, 'colormap_vmax'), (self.widget_colormap_vmax, 'value'), lambda value: value or 1)

        self.widget_colormap_name = widgets.Dropdown(options=colormaps, description='colormap')
        link((self.state, 'colormap_name'), (self.widget_colormap_name, 'label'),
             lambda colormap_name: colormaps.name_from_cmap(colormap_name), lambda name: colormaps[name])

        dlink((self.widget_colormap_mode, 'value'), (self.widget_color.layout, 'display'),
              lambda value: None if value == colormap_mode_options[0] else 'none')
        dlink((self.widget_colormap_mode, 'value'), (self.widget_colormap.layout, 'display'),
              lambda value: None if value == colormap_mode_options[1] else 'none')
        dlink((self.widget_colormap_mode, 'value'), (self.widget_colormap_att.layout, 'display'),
              lambda value: None if value == colormap_mode_options[1] else 'none')
        dlink((self.widget_colormap_mode, 'value'), (self.widget_colormap_v.layout, 'display'),
              lambda value: None if value == colormap_mode_options[1] else 'none')
        self.children = (self.widget_colormap_mode, self.widget_color,
                         self.widget_colormap_att, self.widget_colormap_v,
                         self.widget_colormap_name)
