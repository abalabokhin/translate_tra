use std::fs;
use std::env;
use std::path::Path;

fn main() {
    let args : Vec<String> = env::args().collect();
    let filename = &args[1];
    let mut data: Vec<u8> = fs::read(filename).unwrap();
    let sleep_i_offset = u32::from_le_bytes(data[0xc0..0xc0+4].try_into().unwrap());
    let sleep_i_offset = usize::try_from(sleep_i_offset).unwrap();
    let day_probability:Vec<u8> = data[sleep_i_offset+0xa8..sleep_i_offset+0xa8+2].try_into().unwrap();
    let night_probability:Vec<u8> = data[sleep_i_offset+0xaa..sleep_i_offset+0xaa+2].try_into().unwrap();
    let day_old = u16::from_le_bytes(day_probability.try_into().unwrap());
    let night_old = u16::from_le_bytes(night_probability.try_into().unwrap());
    if night_old > 0 && day_old > 0 {
        let path = Path::new(filename);
        let new_night = (100. - (f32::powf(1. - f32::from(night_old) / 100., 0.125)) * 100.).ceil() as u16;
        let new_day = (100. - (f32::powf(1. - f32::from(day_old) / 100., 0.125)) * 100.).ceil() as u16;
        print!("{}, {}, {} -> {}, {}\n", filename, day_old, night_old, new_day, new_night);
        let new_night = new_night.to_le_bytes();
        let new_day = new_day.to_le_bytes();
        data[sleep_i_offset+0xa8] = new_day[0];
        data[sleep_i_offset+0xa9] = new_day[1];
        data[sleep_i_offset+0xaa] = new_night[0];
        data[sleep_i_offset+0xab] = new_night[1];
        let _ = fs::write(filename, data);
    }
}
