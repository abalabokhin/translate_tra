use std::fs;
use std::env;
use std::path::Path;

fn main() {
    let args : Vec<String> = env::args().collect();
    let filename = &args[1];
    let data: Vec<u8> = fs::read(filename).unwrap();
    let sleep_i_offset = u32::from_le_bytes(data[0xc0..0xc0+4].try_into().unwrap());
    let sleep_i_offset = usize::try_from(sleep_i_offset).unwrap();
    let day_probability:Vec<u8> = data[sleep_i_offset+0xa8..sleep_i_offset+0xa8+2].try_into().unwrap();
    let night_probability:Vec<u8> = data[sleep_i_offset+0xaa..sleep_i_offset+0xaa+2].try_into().unwrap();
    let day_probability = u16::from_le_bytes(day_probability.try_into().unwrap());
    let night_probability = u16::from_le_bytes(night_probability.try_into().unwrap());
    if night_probability > 0 && day_probability > 0 {
        let path = Path::new(filename);
        let filename = path.file_name().unwrap();
        print!("{}, {}, {}\n", filename.to_str().unwrap(), day_probability, night_probability);
    }
}
