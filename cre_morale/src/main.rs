use std::fs;
use std::env;
use std::path::Path;
use std::fs::read_to_string;

fn read_lines(filename: &str) -> Vec<String> {
    read_to_string(filename)
        .unwrap()  // panic on possible file-reading errors
        .lines()  // split the string into an iterator of string slices
        .map(String::from)  // make each slice into a string
        .collect()  // gather them together into a vector
}

fn main() {
    let args : Vec<String> = env::args().collect();
    let filename = &args[1];
    let mut data: Vec<u8> = fs::read(filename).unwrap();
    let morale_break = u8::from_le_bytes(data[0x240..0x240+1].try_into().unwrap());
    let morale_recovery_time = u16::from_le_bytes(data[0x242..0x242+2].try_into().unwrap());
    print!("{}, {}, {}\n", filename, morale_break, morale_recovery_time);
    let cres = read_lines("cre_to_fix.txt");
    let new_mb = 5u8.to_le_bytes();
    let new_mrt = 60u16.to_le_bytes();

    for cre in cres {
        if filename.contains(&cre) {
            data[0x240] = new_mb[0];
            data[0x242] = new_mrt[0];
            data[0x243] = new_mrt[1];
            let _ = fs::write(filename, data);
            break;
        }
    }
}
