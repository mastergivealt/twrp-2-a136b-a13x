-include device/samsung/a13x/generated.mk

# The TWRP minimal manifest strips several AOSP product files, so inherit them only if present.
$(call inherit-product-if-exists, $(SRC_TARGET_DIR)/product/base.mk)
$(call inherit-product-if-exists, $(SRC_TARGET_DIR)/product/embedded.mk)
$(call inherit-product-if-exists, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)
ifneq ($(GEN_USERSPACE_BITS),32)
$(call inherit-product-if-exists, $(SRC_TARGET_DIR)/product/core_64_bit_only.mk)
endif
$(call inherit-product, vendor/twrp/config/common.mk)

PRODUCT_NAME := twrp_a13x
PRODUCT_DEVICE := a13x
PRODUCT_BRAND := samsung
PRODUCT_MODEL := Galaxy A13 5G
PRODUCT_MANUFACTURER := samsung

PRODUCT_USE_DYNAMIC_PARTITIONS := true
