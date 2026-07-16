#include <linux/init.h>
#include <linux/module.h>
#include <linux/power_supply.h>

#define DRIVER_NAME "headset_battery_test"

static struct power_supply *headset_power_supply;

static int battery_capacity = 50;

static int set_battery_capacity(
    const char *value,
    const struct kernel_param *parameter
)
{
    int new_capacity;
    int result;

    result = kstrtoint(value, 10, &new_capacity);
    if (result < 0)
        return result;

    if (new_capacity < 0 || new_capacity > 100)
        return -EINVAL;

    battery_capacity = new_capacity;

    if (headset_power_supply)
        power_supply_changed(headset_power_supply);

    pr_info(
        DRIVER_NAME ": battery capacity updated to %d%%\n",
        battery_capacity
    );

    return 0;
}

static const struct kernel_param_ops battery_capacity_ops = {
    .set = set_battery_capacity,
    .get = param_get_int,
};

module_param_cb(
    battery_capacity,
    &battery_capacity_ops,
    &battery_capacity,
    0644
);

MODULE_PARM_DESC(
    battery_capacity,
    "Headset battery percentage"
);

static enum power_supply_property headset_properties[] = {
    POWER_SUPPLY_PROP_STATUS,
    POWER_SUPPLY_PROP_ONLINE,
    POWER_SUPPLY_PROP_CAPACITY,
    POWER_SUPPLY_PROP_SCOPE,
    POWER_SUPPLY_PROP_MODEL_NAME,
    POWER_SUPPLY_PROP_MANUFACTURER,
    POWER_SUPPLY_PROP_SERIAL_NUMBER,
};

static int headset_get_property(
    struct power_supply *psy,
    enum power_supply_property property,
    union power_supply_propval *value
)
{
    switch (property) {
    case POWER_SUPPLY_PROP_STATUS:
        value->intval = POWER_SUPPLY_STATUS_DISCHARGING;
        return 0;

    case POWER_SUPPLY_PROP_ONLINE:
        value->intval = 1;
        return 0;

    case POWER_SUPPLY_PROP_CAPACITY:
        value->intval = clamp(battery_capacity, 0, 100);
        return 0;

    case POWER_SUPPLY_PROP_SCOPE:
        value->intval = POWER_SUPPLY_SCOPE_DEVICE;
        return 0;

    case POWER_SUPPLY_PROP_MODEL_NAME:
        value->strval = "PRO X Wireless Gaming Headset";
        return 0;

    case POWER_SUPPLY_PROP_MANUFACTURER:
        value->strval = "Logitech";
        return 0;

    case POWER_SUPPLY_PROP_SERIAL_NUMBER:
        value->strval = "virtual-headset-0";
        return 0;

    default:
        return -EINVAL;
    }
}

static const struct power_supply_desc headset_power_supply_desc = {
    .name = "headset_battery_0",
    .type = POWER_SUPPLY_TYPE_BATTERY,
    .properties = headset_properties,
    .num_properties = ARRAY_SIZE(headset_properties),
    .get_property = headset_get_property,
};

static int __init headset_battery_init(void)
{
    struct power_supply_config config = {};

    headset_power_supply = power_supply_register(
        NULL,
        &headset_power_supply_desc,
        &config
    );

    if (IS_ERR(headset_power_supply)) {
        pr_err(
            DRIVER_NAME ": failed to register power supply: %ld\n",
            PTR_ERR(headset_power_supply)
        );
        return PTR_ERR(headset_power_supply);
    }

    pr_info(
        DRIVER_NAME ": registered virtual headset battery at %d%%\n",
        battery_capacity
    );

    return 0;
}

static void __exit headset_battery_exit(void)
{
    power_supply_unregister(headset_power_supply);
    pr_info(DRIVER_NAME ": virtual headset battery removed\n");
}

module_init(headset_battery_init);
module_exit(headset_battery_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Evan Reyes");
MODULE_DESCRIPTION("Proof-of-concept virtual power supply for a wireless headset");
MODULE_VERSION("0.1");
