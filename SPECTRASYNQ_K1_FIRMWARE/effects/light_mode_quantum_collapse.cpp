#include "lightshow_modes.h"

void light_mode_quantum_collapse() {
  // Define parameters for quantum collapse effect
  static SQ15x16 collapse_intensity = 0.75;
  static SQ15x16 field_smoothing = 0.90;
  static SQ15x16 collapse_probability = 0.003;
  static SQ15x16 field_disturbance = 0.05;
  
  // Define probability field and wave states
  static SQ15x16 wave_probabilities[NATIVE_RESOLUTION];
  static SQ15x16 fluid_velocity[NATIVE_RESOLUTION];
  static SQ15x16 temp_field[NATIVE_RESOLUTION];
  static SQ15x16 temp_fluid[NATIVE_RESOLUTION];
  
  // Animation timing variables
  static SQ15x16 animation_phase = 0;
  static SQ15x16 wave_phase = 0;
  
  // Safely update animation phases
  animation_phase += SQ15x16(0.01) * SQ15x16(CONFIG.MOOD);
  if (animation_phase > SQ15x16(1.0)) animation_phase -= SQ15x16(1.0);
  
  wave_phase += SQ15x16(0.003) * SQ15x16(CONFIG.MOOD);
  if (wave_phase > SQ15x16(1.0)) wave_phase -= SQ15x16(1.0);
  
  // Audio reactivity
  static SQ15x16 bass_energy = 0;
  static SQ15x16 mid_energy = 0;
  static SQ15x16 high_energy = 0;
  
  // Calculate spectral energy in different bands (safely)
  bass_energy = 0;
  mid_energy = 0;
  high_energy = 0;
  
  for (int i = 0; i < 16 && i < NUM_FREQS; i++) {
    if (isfinite(float(spectrogram_smooth[i]))) {
      bass_energy += spectrogram_smooth[i] * spectrogram_smooth[i];
    }
  }
  bass_energy /= 16.0;
  
  for (int i = 16; i < 32 && i < NUM_FREQS; i++) {
    if (isfinite(float(spectrogram_smooth[i]))) {
      mid_energy += spectrogram_smooth[i] * spectrogram_smooth[i];
    }
  }
  mid_energy /= 16.0;
  
  for (int i = NUM_FREQS / 2; i < NUM_FREQS; i++) {
    if (isfinite(float(spectrogram_smooth[i]))) {
      high_energy += spectrogram_smooth[i] * spectrogram_smooth[i];
    }
  }
  high_energy /= SQ15x16(NUM_FREQS / 2);
  
  // Scale energy values
  bass_energy = bass_energy * 5.0;
  mid_energy = mid_energy * 4.0;
  high_energy = high_energy * 3.0;
  
  // Clamp to reasonable values
  if (bass_energy > 5.0) bass_energy = 5.0;
  if (mid_energy > 5.0) mid_energy = 5.0;
  if (high_energy > 5.0) high_energy = 5.0;

  // Store previous state
  memcpy(temp_field, wave_probabilities, sizeof(SQ15x16) * NATIVE_RESOLUTION);
  memcpy(temp_fluid, fluid_velocity, sizeof(SQ15x16) * NATIVE_RESOLUTION);

  // Apply quantum simulation to entire strip
  for (int i = 1; i < NATIVE_RESOLUTION - 1; i++) {
    // Laplacian calculation
    SQ15x16 laplacian = temp_field[i-1] - (temp_field[i] * 2.0) + temp_field[i+1];
    
    // Update fluid velocity with smoothing
    fluid_velocity[i] = fluid_velocity[i] * field_smoothing + laplacian * 0.02;
    
    // Update wave probability
    wave_probabilities[i] = temp_field[i] + fluid_velocity[i];

    // Add audio reactivity disturbance based on position
    if (i < NATIVE_RESOLUTION/3) {
      fluid_velocity[i] += bass_energy * 0.01 * (random_float() - 0.5);
    } else if (i < 2*NATIVE_RESOLUTION/3) {
      fluid_velocity[i] += mid_energy * 0.01 * (random_float() - 0.5);
    } else {
      fluid_velocity[i] += high_energy * 0.01 * (random_float() - 0.5);
    }
    
    // Quantum Collapse Probability
    SQ15x16 collapse_chance = collapse_probability * (1.0 + audio_vu_level * 3.0 + bass_energy * 2.0);
    if (random_float() < float(collapse_chance)) {
      wave_probabilities[i] = 1.0; // Collapse
      
      // Add disturbance to neighbors
      if (i > 1) wave_probabilities[i-1] += field_disturbance * (random_float() - 0.5);
      if (i < NATIVE_RESOLUTION - 2) wave_probabilities[i+1] += field_disturbance * (random_float() - 0.5);
    }
    
    // Clamp probability
    if (wave_probabilities[i] < 0.0) wave_probabilities[i] = 0.0;
    if (wave_probabilities[i] > 1.0) wave_probabilities[i] = 1.0;
  }
  
  // Handle boundaries
  wave_probabilities[0] = wave_probabilities[1];
  wave_probabilities[NATIVE_RESOLUTION-1] = wave_probabilities[NATIVE_RESOLUTION-2];

  // Visualization
  bool render_secondary = vp_render_secondary_channel;
  bool palette_owns_colour = palette_owns_render_colour_source();
  uint8_t palette_to_use = render_secondary ? SECONDARY_PALETTE_INDEX : CONFIG.PALETTE_INDEX;
  const CRGBPalette16& pal = cached_gradient_palette(palette_to_use, render_secondary);
  for (int i = 0; i < NATIVE_RESOLUTION; i++) {
    // Position as a fraction (0-1)
    SQ15x16 position = SQ15x16(i) / SQ15x16(NATIVE_RESOLUTION);
    
    // Calculate brightness based on wave probability
    SQ15x16 brightness = wave_probabilities[i] * CONFIG.PHOTONS;
    
    // Apply contrast iterations
    for (uint8_t j = 0; j < floor(CONFIG.SQUARE_ITER); j++) {
      brightness = brightness * brightness;
    }
    
    // Apply fractional iteration
    float fract_iter = CONFIG.SQUARE_ITER - floor(CONFIG.SQUARE_ITER);
    if (fract_iter > 0.01) {
      SQ15x16 squared = brightness * brightness;
      brightness = brightness * (1.0 - fract_iter) + squared * fract_iter;
    }
    
    // Calculate hue using position, chroma, AND fluid velocity for dynamism
    // SQ15x16 velocity_mod = fluid_velocity[i] * 0.5; // Scale velocity effect - Removed for palette mode
    // SQ15x16 hue_val = position + CONFIG.CHROMA + hue_position + velocity_mod;
    
    // Generate color
    if (palette_owns_colour) {
        // --- Palette Mode ---
        // Map position and probability/brightness to palette index
        uint8_t index = uint8_t(float(position) * 192) + uint8_t(float(brightness) * 63); // Example mapping
        // Use the CRGBPalette16 with ColorFromPalette
        CRGB rgb_color = ColorFromPalette(pal, palette_index_with_phase(index), uint8_t(float(brightness) * 255));
        // Convert to CRGB16
        leds_16[i] = crgb_to_crgb16(rgb_color);
    } else {
        // --- Original HSV Mode ---
        SQ15x16 velocity_mod = fluid_velocity[i] * 0.5; // Use velocity mod only in HSV mode
        SQ15x16 hue_val = position + CONFIG.CHROMA + hue_position + velocity_mod;
        
        // Ensure hue wraps correctly
        while (hue_val < 0.0) hue_val += 1.0;
        while (hue_val >= 1.0) hue_val -= 1.0;
        
        // Final Safety Checks for HSV components
        SQ15x16 final_sat = CONFIG.SATURATION;
        if (!isfinite(float(hue_val)) || !isfinite(float(final_sat)) || !isfinite(float(brightness))) {
           if (debug_mode) { USBSerial.print("!!! WARNING [QC]: Invalid final HSV components! i="); USBSerial.println(i); }
           hue_val = 0; final_sat = 1.0; brightness = 0; // Reset problematic components
        }
        leds_16[i] = hsv(hue_val, final_sat, brightness);
    }
  }
  
  // Explicitly handle mirroring if needed
  if (CONFIG.MIRROR_ENABLED) {
    // Here we don't use mirror_image_downwards() to avoid dependency on that function
    uint16_t half_res = NATIVE_RESOLUTION >> 1;
    for (uint16_t i = 0; i < half_res; i++) {
      leds_16[half_res - 1 - i] = leds_16[half_res + i];
    }
  }
}
