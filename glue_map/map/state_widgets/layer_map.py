import ipyvuetify as v
import traitlets
from glue_jupyter.state_traitlets_helpers import GlueState
from glue_jupyter.vuetify_helpers import link_glue_choices, link_glue

__all__ = ["MapLayerStateWidget"]


class MapLayerStateWidget(v.VuetifyTemplate):
    template = (__file__, "layer_map.vue")

    glue_state = GlueState().tag(sync=True)

    data_att_items = traitlets.List().tag(sync=True)
    data_att_selected = traitlets.Int().tag(sync=True)

    #color_att_items = traitlets.List().tag(sync=True)
    #color_att_selected = traitlets.Int(allow_none=True).tag(sync=True)
    #cmap_items = traitlets.List().tag(sync=True)
    #cmap_selected = traitlets.Int(allow_none=False).tag(sync=True)
    as_steps = traitlets.Bool(False).tag(sync=True)

    def __init__(self, layer_state):
        super().__init__()
        print("I am making a MapLayerStateWidget")

        self.layer_state = layer_state
        self.glue_state = layer_state

        link_glue_choices(self, layer_state, "data_att")
        link_glue(self, 'as_steps', layer_state)

        #link_glue_choices(self, layer_state, "color_att")
        #link_glue_choices(self, layer_state, "cmap")
