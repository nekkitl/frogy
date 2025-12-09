#!/bin/bash
export HOMEBREW_NO_ENV_HINTS=true
echo -e "
           .,;::::,..      ......      .,:llllc;'.
        .cxdolcccloddl;:looooddooool::xxdlc:::clddl.
       cxo;'',;;;,,,:ododkOOOOOOOOkdxxl:,';;;;,,,:odl
      od:,;,...x0c:c;;ldox00000000dxdc,,:;00...,:;;cdl
     'dc,;.    ..  .o;:odoOOOOOOOOodl,;;         ::;od.
     'ol';          :o;odlkkkkkkkxodl,d          .o;ld.
     .do,o..........docddoxxxxxxxxodo;x,.........:d;od'
     ;odlcl,......,odcdddodddddddddddl:d:.......:dcodl:.
    ;clodocllcccloolldddddddddddddddddoclllccclollddolc:
   ,:looddddollllodddddddddddddddddddddddollllodddddooc:,
   ':lloddddddddddddddddxxdddddddodxddddddddddddddddoll:'
    :cllclodddddddddddddxloddddddllddddddddddddddolcllc:
     :cloolclodxxxdddddddddddddddddddddddxxxxollclool:,
       ::cloolllllodxxxxxxxxxxxxxxkkkxxdolllllooolc:;
         .::clooddoollllllllllllllllllloodddolcc:,
              ,:cclloodddxxxxxxxxxdddoollcc::.
                     .,:ccccccccccc:::.
"
echo "Frogy - Darwin Installer by nekkitl"
if test -e /usr/local/bin/brew; then
    echo "Brew found..."
else
    echo "Brew not found, installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
echo "Updating brew..."
brew update > /dev/null
echo "Installing tools..."
brew install httpx subfinder dnsx katana findomain python@3.11 jq go unzip whois libpcap gnu-sed 2> /dev/null
echo "Cleanup cache..."
brew cleanup 2>/dev/null
echo "Installing Python requirements..."
python3 -m pip install --upgrade pip 2>/dev/null

chmod +x frogy.py
echo "Enter user password to install supply libs..."
for tool in {amass,anew,waybackurls,unfurl}
do
    sudo cp ./libs/$tool/$tool /usr/local/bin/$tool
    if test -e /usr/local/bin/$tool; then
        echo -e "$tool installed."
    else
        echo -e "$tool not installed. Please chk permissons and try again."
    fi
done

echo ""
echo "Installation complete!"
echo "Run: python3 frogy.py example.com"
