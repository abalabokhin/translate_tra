#if !defined H_UNDAT
#define H_UNDAT

#include <stdint.h>

#define UNCOMPRESSED (0x01)
#define COMPRESSED   (0x02)
#define DIRECTORY    (0x400)
#define TAB_LEN      (0x04)
#define UNK1_LEN     (0x10) // 16 bytes
#define UNK2_LEN     (0x04) // 4 bytes
#define UNKJUNK_LEN  (0x14) // 20 bytes
#define MAXPATH      (0xFF)

enum EErrorLevels
{
	none,
	wrngargs,
	notfound,
	nomem,
	nospace,
	cannotopen,
	cannotcreat,
	cannotlist,
	cantmkdirdp,
	exception    = 254,
	other        = 255
};

enum EListType
{
	nolist,
	wide,
	full
};

#pragma pack(push, 1)
struct STreeItem
{
public:
  //int   NameSize;  - have to  read -
  //char *Name;      - them manually -
	int32_t Unknown1;
	int32_t Type;
	int32_t RealSize;
	int32_t PackedSize;
	int32_t Offset;
	int32_t ParentDirIndex;
	int32_t FirstChildIndex;
	int32_t LastChildIndex;
};
#pragma pack(pop)

#endif
