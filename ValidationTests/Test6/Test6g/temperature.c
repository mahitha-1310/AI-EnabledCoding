/*
 * temperature.c
 *
 * Purpose:
 *   Implement temperature conversion and validation helpers for Test6g.
 *
 * Goal:
 *   Provide functions for converting between Celsius, Fahrenheit, and Kelvin, and to verify valid Celsius inputs.
 */

#include "temperature.h"

#define ABSOLUTE_ZERO_C -273.15

/*
 * celsius_to_fahrenheit
 *
 * Convert a Celsius value to Fahrenheit.
 */
double celsius_to_fahrenheit(double celsius) {
    return (celsius * 9.0 / 5.0) + 32.0;
}

/*
 * fahrenheit_to_celsius
 *
 * Convert a Fahrenheit value to Celsius.
 */
double fahrenheit_to_celsius(double fahrenheit) {
    return (fahrenheit - 32.0) * 5.0 / 9.0;
}

/*
 * celsius_to_kelvin
 *
 * Convert a Celsius value to Kelvin if the Celsius value is valid.
 * If the input is below absolute zero, return -1.0.
 */
double celsius_to_kelvin(double celsius) {
    if (!is_valid_celsius(celsius)) {
        return -1.0;
    }
    return celsius + 273.15;
}

/*
 * is_valid_celsius
 *
 * Return 1 if the Celsius temperature is at or above absolute zero, otherwise return 0.
 */
int is_valid_celsius(double celsius) {
    return celsius >= ABSOLUTE_ZERO_C;
}
