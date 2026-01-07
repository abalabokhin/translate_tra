// ToEExtract.cpp
//
// Refactored to use C++17 std::filesystem and std::fstream
// Added Packing capability.

#include <iostream>
#include <iomanip>
#include <fstream>
#include <string>
#include <vector>
#include <ctime>
#include <map>
#include <filesystem>
#include <cstring>
#include <algorithm>
#include <zlib.h>
#include "ToEExtract.h"

using namespace std;
namespace fs = std::filesystem;

// --- Global helper for Extraction ---
map<int, fs::path> dir_list;

// --- Helper Functions ---

inline void PrintWelcome()
{
	cout << endl << "ToEExtract v2.2 (C++17 Port + Packer) by Zane" << endl
		 << "Based on Arcanum's Undat v1.0 by MatuX" << endl << endl;
}

inline void PrintUsage() { 
    cout << "Usage:" << endl
         << "  Extract: ToEExtract e <datfile> [destdir] [-l|-lf]" << endl
         << "  Pack:    ToEExtract p <srcdir> <datfile> [-u]" << endl
         << "           -u: Disable compression (uncompressed)" << endl;
}

// Case insensitive string comparison
bool CaseInsensitiveCompare(const string& a, const string& b) {
    return lexicographical_compare(
        a.begin(), a.end(),
        b.begin(), b.end(),
        [](unsigned char c1, unsigned char c2) { return tolower(c1) < tolower(c2); }
    );
}

// --- Packing Logic ---

struct Node {
    string name;
    fs::path fullPath; // Source path
    bool isDir;
    int index; // Assigned index in the flat list
    
    // Tree links
    Node* parent = nullptr;
    vector<Node*> children;
    
    // DAT properties
    int32_t packedSize = 0;
    int32_t realSize = 0;
    int32_t offset = 0;
    int32_t type = 0;
    
    int32_t parentIndex = -1;
    int32_t firstChildIndex = -1;
    int32_t lastChildIndex = -1; // Or NextSiblingIndex for files/root
    int32_t nextSiblingIndex = -1; // Helper for files/root
};

// Recursively build tree
void BuildTree(const fs::path& path, Node* parent, vector<Node*>& allNodes) {
    if (!fs::exists(path)) return;

    // Iterate directory
    vector<fs::directory_entry> entries;
    for (const auto& entry : fs::directory_iterator(path)) {
        if (entry.path().filename() == "." || entry.path().filename() == "..") continue;
        entries.push_back(entry);
    }

    // Sort by name case-insensitive
    sort(entries.begin(), entries.end(), [](const fs::directory_entry& a, const fs::directory_entry& b) {
        return CaseInsensitiveCompare(a.path().filename().string(), b.path().filename().string());
    });

    for (const auto& entry : entries) {
        Node* node = new Node();
        node->name = entry.path().filename().string();
        node->fullPath = entry.path();
        node->isDir = entry.is_directory();
        node->parent = parent;
        
        allNodes.push_back(node);
        if (parent) {
            parent->children.push_back(node);
        }

        if (node->isDir) {
            node->type = DIRECTORY;
            BuildTree(entry.path(), node, allNodes);
        } else {
             node->type = COMPRESSED; // Default
        }
    }
}

// Flatten tree (DFS)
void FlattenTree(const vector<Node*>& roots, vector<Node*>& flatList) {
    for (Node* node : roots) {
        flatList.push_back(node);
        if (node->isDir) {
            FlattenTree(node->children, flatList);
        }
    }
}

// Helper to find the index where the subtree rooted at 'node' ends (exclusive)
int GetSubtreeEndIndex(Node* node) {
    if (!node->isDir || node->children.empty()) {
        return node->index + 1;
    }
    return GetSubtreeEndIndex(node->children.back());
}

void PackMode(string srcDir, string datFile, bool compressEnabled) {
    cout << "Packing '" << srcDir << "' into '" << datFile << "' (Compression: " << (compressEnabled ? "ON" : "OFF") << ")..." << endl;

    if (!fs::exists(srcDir) || !fs::is_directory(srcDir)) {
        cerr << "Error: Source directory does not exist or is not a directory." << endl;
        return;
    }

    // 1. Build Tree
    vector<Node*> allNodes; // To manage memory
    vector<Node*> roots;    // Top level nodes
    
    {
        vector<fs::directory_entry> entries;
        for (const auto& entry : fs::directory_iterator(srcDir)) {
            entries.push_back(entry);
        }
        sort(entries.begin(), entries.end(), [](const fs::directory_entry& a, const fs::directory_entry& b) {
            return CaseInsensitiveCompare(a.path().filename().string(), b.path().filename().string());
        });

        for (const auto& entry : entries) {
            Node* node = new Node();
            node->name = entry.path().filename().string();
            node->fullPath = entry.path();
            node->isDir = entry.is_directory();
            node->parent = nullptr; 
            roots.push_back(node);
            allNodes.push_back(node);

            if (node->isDir) {
                node->type = DIRECTORY;
                BuildTree(entry.path(), node, allNodes);
            } else {
                node->type = COMPRESSED;
            }
        }
    }

    // 2. Flatten
    vector<Node*> flatList;
    FlattenTree(roots, flatList);

    // 3. Assign Indices & Calculate Links
    for (size_t i = 0; i < flatList.size(); ++i) {
        flatList[i]->index = (int)i;
    }

    for (Node* node : flatList) {
        // Parent Index
        if (node->parent) {
            node->parentIndex = node->parent->index;
        } else {
            node->parentIndex = -1;
        }

        if (node->isDir) {
            if (!node->children.empty()) {
                node->firstChildIndex = node->children.front()->index;
                node->lastChildIndex = GetSubtreeEndIndex(node->children.back());
            } else {
                 node->firstChildIndex = -1;
                 node->lastChildIndex = -1; 
            }

            if (node->parent == nullptr) {
                auto it = find(roots.begin(), roots.end(), node);
                if (it != roots.end() && (it + 1) != roots.end()) {
                    node->nextSiblingIndex = (*(it + 1))->index;
                } else {
                    node->nextSiblingIndex = -1;
                }
                node->lastChildIndex = node->nextSiblingIndex;
            }
        } else {
            node->nextSiblingIndex = -1;
            vector<Node*>* siblings = nullptr;
            if (node->parent) siblings = &node->parent->children;
            else siblings = &roots;
            
            if (siblings) {
                auto it = find(siblings->begin(), siblings->end(), node);
                if (it != siblings->end() && (it + 1) != siblings->end()) {
                    node->nextSiblingIndex = (*(it + 1))->index;
                }
            }
            node->lastChildIndex = node->nextSiblingIndex;
        }
    }

    // 4. Write Data
    ofstream out(datFile, ios::binary);
    if (!out.is_open()) {
        cerr << "Error: Could not create DAT file." << endl;
        return;
    }

    cout << "Writing file data..." << endl;
    for (Node* node : flatList) {
        if (!node->isDir) {
            ifstream inFile(node->fullPath, ios::binary | ios::ate);
            if (!inFile.is_open()) {
                cerr << "Warning: Could not read " << node->fullPath << endl;
                continue;
            }
            streamsize size = inFile.tellg();
            node->realSize = (int32_t)size;
            node->offset = (int32_t)out.tellp();

            vector<char> rawData(size);
            inFile.seekg(0, ios::beg);
            inFile.read(rawData.data(), size);

            bool didCompress = false;
            if (compressEnabled) {
                uLongf destLen = compressBound(size);
                vector<Bytef> compressedData(destLen);
                int res = compress(compressedData.data(), &destLen, (const Bytef*)rawData.data(), size);

                if (res == Z_OK && destLen < (uLong)size) {
                    node->type = COMPRESSED;
                    node->packedSize = (int32_t)destLen;
                    out.write((char*)compressedData.data(), destLen);
                    didCompress = true;
                }
            }

            if (!didCompress) {
                node->type = UNCOMPRESSED;
                node->packedSize = node->realSize;
                out.write(rawData.data(), size);
            }
        }
    }

    // 5. Write Tree
    streampos treeStart = out.tellp();
    int32_t filesTotal = (int32_t)flatList.size();
    
    out.write((char*)&filesTotal, sizeof(filesTotal));

    cout << "Writing directory tree..." << endl;
    for (Node* node : flatList) {
        int32_t nameLen = (int32_t)node->name.length() + 1;
        out.write((char*)&nameLen, sizeof(nameLen));
        out.write(node->name.c_str(), nameLen);
        
        STreeItem item;
        item.Unknown1 = 0; 
        item.Type = node->type;
        item.RealSize = node->realSize;
        item.PackedSize = node->packedSize;
        item.Offset = node->offset;
        item.ParentDirIndex = node->parentIndex;
        item.FirstChildIndex = node->firstChildIndex;
        item.LastChildIndex = node->lastChildIndex;
        
        out.write((char*)&item, sizeof(item));
    }
    
    streampos treeEnd = out.tellp();
    int32_t treeSubs = (int32_t)(treeEnd - treeStart) + 28;

    // 6. Write Footer
    char unk1[16] = {0}; 
    out.write(unk1, 16);
    char unk2[] = "1TAD"; 
    out.write(unk2, 4);
    int32_t unk3 = 0x134;
    out.write((char*)&unk3, sizeof(unk3));
    out.write((char*)&treeSubs, sizeof(treeSubs));

    cout << "Packing complete. Created " << datFile << " with " << filesTotal << " items." << endl;
    for (Node* n : allNodes) delete n;
}

// --- Extraction Logic ---

void processpath(int parent_index, int item_index, int item_type, string item_name)
{
    fs::path current_path = item_name;
	if ( parent_index == -1 && item_type != DIRECTORY ) return;
	if ( parent_index == -1 ) {
		dir_list[item_index] = current_path;
		return;
	}
    if (dir_list.find(parent_index) != dir_list.end()) {
        fs::path full_path = dir_list[parent_index] / current_path;
        if ( item_type == DIRECTORY ) dir_list[item_index] = full_path;
    }
}

void ExtractMode(int argc, char* argv[]) {
    if (argc < 3) { PrintUsage(); return; }
    fs::path datfile_path = argv[2];
    fs::path destpath;
    int ilist = nolist;
    if (argc >= 4) {
        string arg3 = argv[3];
        if (arg3 == "-l") ilist = wide;
        else if (arg3 == "-lf") ilist = full;
        else {
            destpath = arg3;
            if (argc >= 5) {
                string arg4 = argv[4];
                if (arg4 == "-l") ilist = wide;
                else if (arg4 == "-lf") ilist = full;
            }
        }
    }
    if (destpath.empty()) destpath = fs::current_path();
    try { if (!fs::exists(destpath)) fs::create_directories(destpath); } catch (...) {}

    ifstream fdat(datfile_path, ios::binary);
	if( !fdat.is_open() ) { cerr << "Could not open DAT file." << endl; return; }

	char unk1[UNK1_LEN], unk2[UNK2_LEN];
	int32_t unk3, treesubs, filestotal;
	fdat.seekg(-0x1C, ios::end);
	fdat.read(unk1, UNK1_LEN);
	fdat.read(unk2, UNK2_LEN);
	fdat.read(reinterpret_cast<char*>(&unk3), 0x04);
	fdat.read(reinterpret_cast<char*>(&treesubs), 0x04);
	fdat.seekg(-treesubs, ios::end);
	fdat.read(reinterpret_cast<char*>(&filestotal), 0x04);
	
	if( ilist == nolist ) {
        cout << "Extracting " << datfile_path << "..." << endl;
        fs::path datdir = destpath / datfile_path.stem(); 
        fs::create_directories(datdir);
        vector<char> name_buffer(MAXPATH);
        STreeItem treeitem;
        int32_t namesize;
		for( int x = 1; x <= filestotal; x++ ) {
			fdat.read(reinterpret_cast<char*>(&namesize), 0x04);
            if (namesize > MAXPATH) namesize = MAXPATH;
			fdat.read(name_buffer.data(), namesize);
            string name(name_buffer.data(), namesize);
            if (!name.empty() && name.back() == '\0') name.pop_back();
			fdat.read(reinterpret_cast<char*>(&treeitem), sizeof(treeitem));
			streampos treepos = fdat.tellg();
			processpath(treeitem.ParentDirIndex, x - 1, treeitem.Type, name);
            fs::path itempath = (treeitem.ParentDirIndex != -1 && dir_list.count(treeitem.ParentDirIndex)) ? 
                                datdir / dir_list[treeitem.ParentDirIndex] / name : datdir / name;
            if (treeitem.Type != DIRECTORY) { if (itempath.has_parent_path()) fs::create_directories(itempath.parent_path()); }
            else fs::create_directories(itempath);
			switch( treeitem.Type ) {
			case COMPRESSED: {
                vector<unsigned char> psbuffer(treeitem.PackedSize), rsbuffer(treeitem.RealSize);
				fdat.seekg(treeitem.Offset, ios::beg);
				fdat.read(reinterpret_cast<char*>(psbuffer.data()), treeitem.PackedSize);
				unsigned long ulrsize = treeitem.RealSize;
				if(uncompress(rsbuffer.data(), &ulrsize, psbuffer.data(), treeitem.PackedSize) == Z_OK) {
                     ofstream outfile(itempath, ios::binary); outfile.write(reinterpret_cast<char*>(rsbuffer.data()), treeitem.RealSize);
                }
				break;
            }
			case UNCOMPRESSED: {
                vector<unsigned char> rsbuffer(treeitem.RealSize);
				fdat.seekg(treeitem.Offset, ios::beg);
				fdat.read(reinterpret_cast<char*>(rsbuffer.data()), treeitem.RealSize);
                ofstream outfile(itempath, ios::binary); outfile.write(reinterpret_cast<char*>(rsbuffer.data()), treeitem.RealSize);
				break;
            }
			}
			fdat.seekg(treepos);
		}
		cout << endl << "Done." << endl;
	} else {
		fs::path lstpath = destpath / datfile_path.filename(); lstpath.replace_extension(".lst");
		ofstream datlst(lstpath);
        vector<char> name_buffer(MAXPATH);
        STreeItem treeitem;
        int32_t namesize;
        datlst << "filestotal: " << filestotal << endl << "------------------" << endl;
		for( int x = 1; x <= filestotal; x++ ) {
			fdat.read(reinterpret_cast<char*>(&namesize), 0x04);
            if (namesize > MAXPATH) namesize = MAXPATH;
			fdat.read(name_buffer.data(), namesize);
            string name(name_buffer.data(), namesize);
            if (!name.empty() && name.back() == '\0') name.pop_back();
			fdat.read(reinterpret_cast<char*>(&treeitem), sizeof(treeitem));
			if( ilist == full ) {
				datlst << "Name: " << name << " | Type: " << treeitem.Type << " | Real: " << treeitem.RealSize << " | Packed: " << treeitem.PackedSize << " | Offset: " << treeitem.Offset << endl;
            } else datlst << name << endl;
		}
	}
	fdat.close();
}

int main(int argc, char* argv[])
{
	PrintWelcome();
    if (argc < 2) { PrintUsage(); return 0; }
    string mode = argv[1];
    if (mode == "e") {
        ExtractMode(argc, argv);
    } else if (mode == "p") {
        if (argc < 4) { PrintUsage(); return 0; }
        bool compress = true;
        if (argc >= 5 && string(argv[4]) == "-u") compress = false;
        PackMode(argv[2], argv[3], compress);
    } else {
        PrintUsage();
    }
	return 0;
}