from dataclasses import dataclass, field
from contextlib import contextmanager
from pathlib import Path
from typing import Union, Protocol, Optional, TextIO, BinaryIO, Iterator
from scp import SCPClient
import paramiko

class RemotablePath(Protocol):
    "Implemented by LocalPath, SCPAddress"
    def _get_local_file(self) -> Path:
        "This gets a local file that can immediately be read."
        ...
    def _close_local_file(self) -> None:
        "This is called after you finish reading a file."
        ...
    
@contextmanager
def remotable_as_local_file(file_source:RemotablePath) -> Iterator[Path]:
    "This returns a local file that can temporarily be used as needed."
    file:Path = file_source._get_local_file()
    try:
        yield file
    except Exception as e:
        raise e
    finally:
        file_source._close_local_file()

@dataclass
class LocalPath:
    path: Path
    
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path).expanduser().absolute()
    
    def __str__(self) -> str:
        return str(self.path)

    def _get_local_file(self)->Path:
        return self.path
    
    def _close_local_file(self)->None:
        "Nothing to do here"
        pass

@dataclass
class SCPAddress:
    user: str | None
    host: str
    path: str
    local_save_path: Path
    "This is the local path that the scp file is saved to temporarily."
    ssh_key_path: Optional[Path] = None
    "The path to ssh key file."
    local_file_exists: bool = field(default=False,init=False)
    "True if we have created a file, but it hasn't been closed yet by our code."
    write_file_back: bool = field(default=False,init=False)
    "True if you want any edits you make on the file to be saved to the remote file. This will overwrite any local edits to that file that have been recieved since you first opened the file."

    
    def __init__(self, address: str, local_path:Path|None=None, ssh_key_path:Path|None=None,write_file_back:bool=False):
        """
        Initializes the SCP Address so you can use a remote file in the same place as a local file

        Parameters
        ----------
        address : str
            The SCP address of the file to use in the format `user@server:/path/to/file` or  `server:/path/to/file`
        local_path : Path | None, optional
            The local path that the file will temporarily be written to locally, by default None which becomes `./file`
        ssh_key_path : Path | None, optional
            This is the path to the ssh key file to the server to be used to get access to the server., by default None
        write_file_back : bool, optional
            True if you want the local file to be written to the remote file after editing finishes (like for a write) but this will overwrite any remote changes that have happened since the initial copy. False if you want to maintain remote data and only read it, by default False
        """

        raise NotImplementedError("""
                                  The SCP Address object seemed to be having SCP Errors that I couldn't quite figure out. 
                                  It seems that when we have a version of penguin running and we are trying to connect to the remote server, it doesn't work.
                                  This is weird because it was working previously when we were testing.
                                  It complains of not being able to connect to the server and timing out, though.
                                  Investigate it more with the `mess_with_scp.py` script.
                                  """)
    

        # Parse user@host:/path
        if '@' in address:
            user_host, path         = address.split(':', 1)
            self.user, self.host    = user_host.split('@', 1)
        else:
            # host:/path format
            self.host, path     = address.split(':', 1)
            self.user           = None
        self.path               = path
        self.local_save_path    = local_path if local_path is not None else (Path(".") / Path(self.path).name).resolve()
        self.ssh_key_path       = Path(ssh_key_path).expanduser().resolve() if ssh_key_path is not None else None
        self.write_file_back    = write_file_back
    
    def __str__(self) -> str:
        if self.user:
            return f"{self.user}@{self.host}:{self.path}"
        return f"{self.host}:{self.path}"
    
    def _get_local_file(self)->Path:
        """Download file if remote, return local path"""
        ssh = paramiko.SSHClient()
        try:
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host, username=self.user, key_filename=str(self.ssh_key_path) if self.ssh_key_path else None, look_for_keys=True)
            
            transport = ssh.get_transport()
            if transport is None: raise ValueError("Failed To Cate a transport object for ssh in _get_local_file.")

            with SCPClient(transport) as scp:
                scp.get(self.path, str(self.local_save_path))
                self.local_file_exists = True
        finally:
            ssh.close()
        return self.local_save_path
     
    def _close_local_file(self)->None:
        "This writes any changes to the local file to the remote location."
        if not self.write_file_back:
            self.local_save_path.unlink() # Delete local file
            self.local_file_exists = False
            return
        
        ssh = paramiko.SSHClient()
        try:
            ssh.load_system_host_keys()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host, username=self.user, key_filename=str(self.ssh_key_path) if self.ssh_key_path else None, look_for_keys=True)
            
            transport = ssh.get_transport()
            if transport is None: raise ValueError("_close_local_file was unable to get a ssh transport object.")

            with SCPClient(transport) as scp:
                scp.put(str(self.local_save_path),self.path)
                self.local_save_path.unlink() # Delete local file
                self.local_file_exists = False
        finally:
            ssh.close()
        
# Usage with a factory function
def parse_remotable_path(location: str, temporary_local_file:Path|None=None, write_back:bool=False,ssh_key_path:Path|None=None) -> RemotablePath:
    """
    Turns a remotable string into a remotable object. This includes files ober scp and local files.

    Parameters
    ----------
    location : str
        This is the string that is parsed to determine the remotable_path.
    temporary_local_file : Path | None, optional
        If you need to create a local file, this is the file that will be used. One in the CWD will be chosen if None provided, by default None
    write_back : bool, optional
        If you require a local file to be copied locally and be written to this will set whether the folder will be copied back. True means it will save the data but overwrite any remote changed but False doesn't save local changes, by default False
    ssh_key_path : Path | None, optional
        This is the path to the ssh key file to authenticate yourself to the ssh server if provided, by default None

    Returns
    -------
    Union[LocalPath, SCPAddress]
        SCPAddress if:
            location matches to patterns `user@server:/path/to/file` and `server:/path/to/file`. Uses arguments [temporary_local_file, write_back, ssh_key_path].

        LocalPath if:
            location could not be parsed into another path. Uses arguments [].
    """
    if ':' in location \
        and not (location[1]==':' and location[0].isupper())\
        and ('@' in location or not location.startswith('/')):
        return SCPAddress(location, 
                          local_path=       temporary_local_file, 
                          write_file_back=  write_back,
                          ssh_key_path=     ssh_key_path
                          )
    return LocalPath(location)


@contextmanager
def remotable_open(file_source:RemotablePath,*args,**kargs) -> Iterator[Union[TextIO, BinaryIO]]:
    """
    Context manager to open a remotable file.
    
    Yields:
        TextIO for text mode ('r', 'w', 'a', etc.)
        BinaryIO for binary mode ('rb', 'wb', 'ab', etc.)
    """
    with remotable_as_local_file(file_source) as local_file:
        try:
            with open(local_file,*args,**kargs) as f:
                yield f
        except Exception as e:
            raise e
    

