// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.
//
// Copyright (c) 2024 - 2025 Upside Down Labs - contact@upsidedownlabs.tech
// Author: Deepak Khatri

#include <Arduino.h>

/** 
** Select your board from list below
** Uncomment only your board macro
**/

// #define BOARD_NANO_CLONE
// #define BOARD_MAKER_NANO
// #define BOARD_NANO_CLASSIC
#define BOARD_UNO_R3
// #define BOARD_GENUINO_UNO
// #define BOARD_UNO_CLONE
// #define BOARD_MAKER_UNO
// #define BOARD_MEGA_2560_R3
// #define BOARD_MEGA_2560_CLONE

// Board specific macros
#if defined(BOARD_UNO_R3)
#define BOARD_NAME "UNO-R3"
#define NUM_CHANNELS 6
#elif defined(BOARD_GENUINO_UNO)
#define BOARD_NAME "GENUINO-UNO"
#define NUM_CHANNELS 6
#elif defined(BOARD_UNO_CLONE) || defined(BOARD_MAKER_UNO)
#define BOARD_NAME "UNO-CLONE"
#define NUM_CHANNELS 6
#elif defined(BOARD_NANO_CLASSIC)
#define BOARD_NAME "NANO-CLASSIC"
#define NUM_CHANNELS 8
#elif defined(BOARD_NANO_CLONE) || defined(BOARD_MAKER_NANO)
#define BOARD_NAME "NANO-CLONE"
#define NUM_CHANNELS 8
#elif defined(BOARD_MEGA_2560_R3)
#define BOARD_NAME "MEGA-2560-R3"
#define NUM_CHANNELS 16
#elif defined(BOARD_MEGA_2560_CLONE)
#define BOARD_NAME "MEGA-2560-CLONE"
#define NUM_CHANNELS 16
#else
#error "Board type not selected, please uncomment your BOARD macro!"
#endif

// Common macros
#define SAMP_RATE 250
#define BAUD_RATE 115200

// defines for setting and clearing register bits
#ifndef cbi
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#endif
#ifndef sbi
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))
#endif

// Global constants and variables
volatile uint16_t adcValues[NUM_CHANNELS];  // Latest ADC values for each channel
volatile bool bufferReady = false;          // New data ready flag
volatile uint8_t currentChannel = 0;        // Current channel being sampled
bool timerStatus = false;                   // Status bit

bool timerStart() {
  timerStatus = true;
  digitalWrite(LED_BUILTIN, HIGH);
  // Enable Timer1 Compare A interrupt
  TIMSK1 |= (1 << OCIE1A);
  return true;
}

bool timerStop() {
  timerStatus = false;
  bufferReady = false;
  digitalWrite(LED_BUILTIN, LOW);
  // Disable Timer1 Compare A interrupt
  TIMSK1 &= ~(1 << OCIE1A);
  return true;
}

// ISR for Timer1 Compare A match (called based on the sampling rate)
ISR(TIMER1_COMPA_vect) {
  // Read all configured channels
  for (currentChannel = 0; currentChannel < NUM_CHANNELS; currentChannel++) {
    // On Uno, analogRead(0) is A0, analogRead(1) is A1 and so on
    adcValues[currentChannel] = analogRead(currentChannel);
  }
  bufferReady = true;
}

void timerBegin(float sampling_rate) {
  cli();  // Disable global interrupts

  // Set ADC prescaler division factor to 16
  sbi(ADCSRA, ADPS2);  // 1
  cbi(ADCSRA, ADPS1);  // 0
  cbi(ADCSRA, ADPS0);  // 0

  // Calculate OCR1A based on the interval
  // OCR1A = (16MHz / (Prescaler * Desired Time)) - 1
  // Prescaler options: 1, 8, 64, 256, 1024
  unsigned long ocrValue = (16000000UL / (8UL * (unsigned long)sampling_rate)) - 1UL;

  // Configure Timer1 for CTC mode (Clear Timer on Compare Match)
  TCCR1A = 0;  // Clear control register A
  TCCR1B = 0;  // Clear control register B
  TCNT1 = 0;   // Clear counter value

  // Set the calculated value in OCR1A register
  OCR1A = ocrValue;

  // Set CTC mode (WGM12 bit) and set the prescaler to 8
  TCCR1B |= (1 << WGM12) | (1 << CS11);  // Prescaler = 8

  sei();  // Enable global interrupts
}

void setup() {
  Serial.begin(BAUD_RATE);
  while (!Serial) {
    ;  // Wait for serial port to connect. Needed for native USB
  }

  // Status LED
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  // Setup timer
  timerBegin(SAMP_RATE);

  // Optional: let the user know board type
  Serial.print("Ready on board: ");
  Serial.println(BOARD_NAME);
  Serial.println("Send START, STOP, WHORU or STATUS followed by Enter");
}

void loop() {

  // Handle commands from Serial Monitor
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();         // Remove extra spaces or newline characters
    command.toUpperCase();  // Normalize to uppercase for case insensitivity

    if (command == "WHORU") {
      Serial.println(BOARD_NAME);
    } else if (command == "START") {
      timerStart();
      Serial.println("ACQUISITION STARTED");
    } else if (command == "STOP") {
      timerStop();
      Serial.println("ACQUISITION STOPPED");
    } else if (command == "STATUS") {
      Serial.println(timerStatus ? "RUNNING" : "STOPPED");
    } else {
      Serial.println("UNKNOWN COMMAND");
    }
  }

  // Print data when there is a fresh sample from the ISR
  if (timerStatus && bufferReady) {
    noInterrupts();           // Protect adcValues while we read them
    uint16_t localCopy[NUM_CHANNELS];
    for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
      localCopy[i] = adcValues[i];
    }
    bufferReady = false;
    interrupts();

    // Print values as CSV on one line
    for (uint8_t i = 0; i < NUM_CHANNELS; i++) {
      Serial.print(localCopy[i]);
      if (i < NUM_CHANNELS - 1) {
        Serial.print(',');
      }
    }
    Serial.println();
  }
}