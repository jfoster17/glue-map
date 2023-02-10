import ipyvuetify as v
import traitlets
from glue_jupyter.state_traitlets_helpers import GlueState
from glue_jupyter.vuetify_helpers import link_glue_choices

__all__ = ["MapLayerStateWidget"]


class MapLayerStateWidget(v.VuetifyTemplate):
    template = (__file__, "layer_map.vue")

    color_att_items = traitlets.List().tag(sync=True)
    color_att_selected = traitlets.Int(allow_none=True).tag(sync=True)
    colormap_items = traitlets.List().tag(sync=True)
    colormap_selected = traitlets.Int(allow_none=False).tag(sync=True)

    glue_state = GlueState().tag(sync=True)

    def __init__(self, layer_state):
        super().__init__()

        self.glue_state = layer_state

        link_glue_choices(self, layer_state, "color_att")
        link_glue_choices(self, layer_state, "colormap")
