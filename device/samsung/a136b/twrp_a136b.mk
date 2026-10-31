# The TWRP minimal manifest strips several AOSP product files, so inherit them only if present.
$(call inherit-product-if-exists, $(SRC_TARGET_DIR)/product/base.mk)
$(call inherit-product-if-exists, $(SRC_TARGET_DIR)/product/embedded.mk)
$(call inherit-product-if-exists, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)
$(call inherit-product, vendor/twrp/config/common.mk)

-include device/samsung/a136b/generated.mk

PRODUCT_NAME := twrp_a136b
PRODUCT_DEVICE := $(or $(GEN_PRODUCT_DEVICE),a136b)
PRODUCT_BRAND := samsung
PRODUCT_MODEL := Galaxy A13 5G
PRODUCT_MANUFACTURER := samsung

PRODUCT_USE_DYNAMIC_PARTITIONS := true
