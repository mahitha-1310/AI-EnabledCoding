/*
 * temperature.h
 *
 * Purpose:
 *   Declare temperature conversion and validation functions used by Test6g.
 *
 * Goal:
 *   Provide the public interface for converting temperatures and validating Celsius values.
 */

#ifndef TEMPERATURE_H
#define TEMPERATURE_H

/*
 * celsius_to_fahrenheit
 *
 * Convert Celsius to Fahrenheit.
 */
double celsius_to_fahrenheit(double celsius);

/*
 * fahrenheit_to_celsius
 *
 * Convert Fahrenheit to Celsius.
 */
double fahrenheit_to_celsius(double fahrenheit);

/*
 * celsius_to_kelvin
 *
 * Convert Celsius to Kelvin, or return -1.0 for invalid values.
 */
double celsius_to_kelvin(double celsius);

/*
 * is_valid_celsius
 *
 * Return 1 if celsius is above absolute zero, otherwise return 0.
 */
int is_valid_celsius(double celsius);

#endif
