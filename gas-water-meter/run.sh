#!/usr/bin/with-contenv bashio
# ==============================================================================
# Gas & Water Meter Add-on
# Installs the custom integration into Home Assistant
# ==============================================================================

declare -r SOURCE="/usr/share/custom_components/gas_water_meter"
declare -r TARGET="/config/custom_components/gas_water_meter"

bashio::log.info "Gas & Water Meter Add-on starting..."

# Create target directory
mkdir -p /config/custom_components

# Copy or update integration files
if [ -d "${TARGET}" ]; then
    bashio::log.info "Updating existing Gas & Water Meter integration..."
    rm -rf "${TARGET}"
fi

cp -r "${SOURCE}" "${TARGET}"
bashio::log.info "Gas & Water Meter integration installed to ${TARGET}"

# Verify installation
if [ -f "${TARGET}/__init__.py" ] && [ -f "${TARGET}/manifest.json" ]; then
    bashio::log.info "Installation verified successfully."
    bashio::log.notice "Please restart Home Assistant to activate or update the integration."
else
    bashio::log.error "Installation verification failed! Files may be missing."
    exit 1
fi

# Keep the add-on running so it can be monitored
bashio::log.info "Add-on is running. Integration files are installed."
bashio::log.info "You can stop this add-on after restarting Home Assistant."

# Sleep indefinitely
exec sleep infinity
