<template>
    <div>
        <div>
            <v-select :items="lon_att_items" label="longitude" v-model="lon_att_selected"/>
            </v-select>
        </div>
        <div>
            <v-select :items="lat_att_items" label="latitude" v-model="lat_att_selected"/>
            </v-select>
        </div>
    </div>
</template>
<script>
    module.exports = {
    }
</script>
<style>
    .v-toolbar {
    z-index: 500; <!-- ipyleaflet is z-index 400 and we need this on top -->
    }
    .v-navigation-drawer {
    z-index: 99999 !important; <!-- Hack -->
    }
    .v-menu {
    z-index: 99999 !important; <!-- Hack -->
    }

</style>