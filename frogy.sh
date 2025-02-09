#!/bin/bash
################################################################ HELP #################################################################
if [[ $1 == "-h" ]]; then
        echo -e "Usage:"
        echo -e "./frogy.sh [root-domain] [organisation name] [CHAOS dataset]"
        echo -e "Example:"
        echo -e "Root-domain is: example.com"
        echo -e "Organisation is: Internet Assigned Numbers Authority : can be skipped."
        echo -e "Is this program is in the CHAOS dataset? [y/n] : default NO"
        exit 1
fi

################################################################ LETS GO ##############################################################

FROGY_FORK_VER='0.0.2'

echo -e "Frogy - macOS version $FROGY_FORK_VER by nekkitl"
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
############################################################### Input workers ######################################################################
if [[ -n $1 ]]; then
        domain_name=$1
        echo -e "Root domain name: $1"
        if [[ -n $2 ]]; then
                echo -e "Organisation name: $2"
                org=$2
                cdir=$(echo $org | tr '[:upper:]' '[:lower:]' | tr " " "_")
                cwhois=$(echo $org | tr " " "+")
        else
                echo -e "Without organisation name (autosearch)"
                cdir=$(echo $domain_name | tr '[:upper:]' '[:lower:]' | tr " " "_")
                cwhois=$(echo $domain_name | tr " " "+")
        fi

else
        echo -e "Enter the root domain name (eg: frogy.com): "
        read domain_name
        echo -e "Enter the organisation name (E.g., Carbon Black): "
        read org
fi
############################################################### Housekeeping tasks ######################################################################

echo -e "Hold on! some house keeping tasks being done... "
if [[ -d output ]]; then
        :
else
        mkdir output
fi
if [[ -d output/$cdir ]]; then
        echo -e "Creating $org directory in the 'output' folder..."
        rm -r -f output/$cdir
        mkdir output/$cdir
        mkdir output/$cdir/raw_output
        mkdir output/$cdir/raw_output/raw_http_responses
else
        echo -e "Creating $org directory in the 'output' folder... "
        mkdir output/$cdir
        mkdir output/$cdir/raw_output
        mkdir output/$cdir/raw_output/raw_http_responses
fi

############################################################### Subdomain enumeration ######################################################################

#################### CHAOS ENUMERATION ######################

echo -e "Identifying Subdomains "
if [[ -n $3 ]]; then
        answer=$3
else
        if [[ -n $1 ]]; then
                answer="n"
        else
                echo -n "Is this program is in the CHAOS dataset? (y/n)? "
                read answer
        fi
fi
if [ "$answer" != "${answer#[Yy]}" ]; then
        curl -s https://chaos-data.projectdiscovery.io/index.json -o index.json
        chaosvar=$(cat index.json | grep -w $cdir | grep "URL" | sed 's/"URL": "//;s/",//' | xargs)
        if [ -z "$chaosvar" ]; then
                echo -e "Sorry! could not find data in CHAOS DB..."
                subfinder -d $domain_name --silent -o output/$cdir/subfinder.txtls >/dev/null 2>&1
                cat output/$cdir/subfinder.txtls | unfurl domains >>all.txtls
        else
                curl -s "$chaosvar" -O
                unzip -qq *.zip
                cat *.txt >>output/$cdir/chaos.txtls
                cat output/$cdir/chaos.txtls | unfurl domains >>all.txtls
                echo -e "Chaos count: $(cat output/$cdir/chaos.txtls | tr '[:upper:]' '[:lower:]' | anew | wc -l)"
                find . | grep .txt | sed 's/.txt//g' | cut -d "/" -f2 | grep '\.' >>subfinder.domains
                subfinder -dL subfinder.domains --silent -recursive -o output/$cdir/subfinder.txtls >/dev/null 2>&1
                rm subfinder.domains
                cat output/$cdir/subfinder.txtls | unfurl domains >>all.txtls
                rm *.zip
                rm *.txt
        fi
        rm index.json*
else
        :
fi

#################### AMASS ENUMERATION #############################

amass enum -passive -d $domain_name -o output/$cdir/amass.txtls >/dev/null 2>&1
cat output/$cdir/amass.txtls | unfurl domains | anew >>all.txtls
echo -e "Amaas count: $(cat output/$cdir/amass.txtls | tr '[:upper:]' '[:lower:]' | anew | wc -l)"

#################### WayBackEngine  ENUMERATION ######################
# this code is taken from another open-source project at - https://github.com/bing0o/SubEnum/blob/master/subenum.sh

curl -sk "http://web.archive.org/cdx/search/cdx?url=*."$domain_name"&output=txt&fl=original&collapse=urlkey&page=" | awk -F / '{gsub(/:.*/, "", $3); print $3}' | anew | sort -u >>output/$cdir/wayback.txtls
cat output/$cdir/wayback.txtls | unfurl domains >>all.txtls
echo -e "WaybackEngine count: $(cat output/$cdir/wayback.txtls | tr '[:upper:]' '[:lower:]' | anew | wc -l)"

#################### CERTIFICATE ENUMERATION ######################

registrant=$(whois $domain_name | grep "Registrant Organization" | cut -d ":" -f2 | xargs | sed 's/,/%2C/g' | sed 's/ /+/g' | egrep -v '(Whois|whois|WHOIS|domains|DOMAINS|Domains|domain|DOMAIN|Domain|proxy|Proxy|PROXY|PRIVACY|privacy|Privacy|REDACTED|redacted|Redacted|DNStination|WhoisGuard|Protected|protected|PROTECTED)')
if [ -z "$registrant" ]; then
        curl -s "https://crt.sh/?q="$domain_name"&output=json" | jq -r ".[].name_value" | sed 's/*.//g' | anew >>output/$cdir/whois.txtls
else
        curl -sk "https://crt.sh/?O=$registrant&output=json" | tr ',' '\n' | awk -F'"' '/common_name/ {gsub(/\*\./, "", $4); gsub(/\\n/,"\n",$4);print $4}' | sort -u | anew >>output/$cdir/whois.txtls
        curl -s "https://crt.sh/?q=$registrant" | grep -P -i '<TD>([a-zA-Z]+(\.[a-zA-Z]+)+)</TD>' | sed -e 's/^[ \t]*//' | cut -d ">" -f2 | cut -d "<" -f1 | anew >>output/$cdir/whois.txtls
        curl -s "https://crt.sh/?q=$domain_name&output=json" | jq -r ".[].name_value" | sed 's/*.//g' | anew >>output/$cdir/whois.txtls
fi

registrant2=$(whois $domain_name | grep "Registrant Organisation" | cut -d ":" -f2 | xargs | sed 's/,/%2C/g' | sed 's/ /+/g' | egrep -v '(Whois|whois|WHOIS|domains|DOMAINS|Domains|domain|DOMAIN|Domain|proxy|Proxy|PROXY|PRIVACY|privacy|Privacy|REDACTED|redacted|Redacted|DNStination|WhoisGuard|Protected|protected|PROTECTED)')
if [ -z "$registrant2" ]; then
        curl -s "https://crt.sh/?q="$domain_name"&output=json" | jq -r ".[].name_value" | sed 's/*.//g' | anew >>output/$cdir/whois.txtls
else
        curl -s "https://crt.sh/?q="$registrant2"" | grep -a -P -i '<TD>([a-zA-Z]+(\.[a-zA-Z]+)+)</TD>' | sed -e 's/^[ \t]*//' | cut -d ">" -f2 | cut -d "<" -f1 | anew >>output/$cdir/whois.txtls
        curl -s "https://crt.sh/?q="$domain_name"&output=json" | jq -r ".[].name_value" | sed 's/*.//g' | anew >>output/$cdir/whois.txtls
fi
cat output/$cdir/whois.txtls | unfurl domains | anew >>all.txtls
echo -e "Certificate search count: $(cat output/$cdir/whois.txtls | tr '[:upper:]' '[:lower:]' | anew | grep -v " " | grep -v "@" | grep "\." | wc -l)"

#################### FINDOMAIN ENUMERATION ######################

findomain -t $domain_name -q >>output/$cdir/findomain.txtls
cat output/$cdir/findomain.txtls | unfurl domains | anew >>all.txtls
echo -e "Findomain count: $(cat output/$cdir/findomain.txtls | tr '[:upper:]' '[:lower:]' | anew | grep -v " " | grep -v "@" | grep "\." | wc -l)"

#################### DNSCAN ENUMERATION ######################

python3 dnscan/dnscan.py -d %%.$domain_name -w wordlist/subdomains-top1million-5000.txt -D -o output/$cdir/dnstemp.txtls >/dev/null 2>&1
cat output/$cdir/dnstemp.txtls | grep $domain_name | egrep -iv ".(DMARC|spf|=|[*])" | cut -d " " -f1 | anew | sort -u | grep -v " " | grep -v "@" | grep "\." >>output/$cdir/dnscan.txtls
rm output/$cdir/dnstemp.txtls
echo -e "Dnscan: $(cat output/$cdir/dnscan.txtls | tr '[:upper:]' '[:lower:]' | anew | grep -v " " | grep -v "@" | grep "\." | wc -l)"

#################### GATHERING ROOT DOMAINS ######################

python3 rootdomain.py | cut -d " " -f7 | tr '[:upper:]' '[:lower:]' | anew | sed '/^$/d' | grep -v " " | grep -v "@" | grep "\." >>rootdomain.txtls

#################### SUBFINDER2 ENUMERATION ######################

subfinder -dL rootdomain.txtls --silent -o output/$cdir/subfinder2.txtls >/dev/null 2>&1
echo -e "Subfinder count: $(cat output/$cdir/subfinder2.txtls | tr '[:upper:]' '[:lower:]' | anew | grep -v " " | grep -v "@" | grep "\." | wc -l)"
cat output/$cdir/subfinder2.txtls | unfurl domains | anew >>all.txtls

#################### HOUSEKEEPING TASKS #########################

mv rootdomain.txtls output/$cdir/
echo "www.$domain_name" | unfurl domains >>all.txtls
echo "$domain_name" | unfurl domains >>all.txtls
cat all.txtls | tr '[:upper:]' '[:lower:]' | unfurl domains | anew >>$cdir.master
mv $cdir.master output/$cdir/$cdir.master
rm all.txtls

#################### SUBDOMAIN RESOLVER ######################
dnsx -l output/$cdir/$cdir.master -silent -a -aaaa -cname -ns -txt -ptr -mx -soa -axfr -caa -resp -json -o output/$cdir/resolved.json >/dev/null 2>&1
cat output/$cdir/resolved.json | jq . | grep host | cut -d " " -f4 | cut -d '"' -f2 | xargs | tr " " "\n" | anew >live.assets

##CONVERT JSON TO CSV FOR FUTURE##

############################################################################# PERFORMING WEB DISCOVERY  ##################################################################

httpx -fr -nc -silent -l live.assets -p 80,81,82,88,135,143,300,443,554,591,593,832,902,981,993,1010,1024,1311,2077,2079,2082,2083,2086,2087,2095,2096,2222,2480,3000,3128,3306,3333,3389,4243,4443,4567,4711,4712,4993,5000,5001,5060,5104,5108,5357,5432,5800,5985,6379,6543,7000,7170,7396,7474,7547,8000,8001,8008,8014,8042,8069,8080,8081,8083,8085,8088,8089,8090,8091,8118,8123,8172,8181,8222,8243,8280,8281,8333,8443,8500,8834,8880,8888,8983,9000,9043,9060,9080,9090,9091,9100,9200,9443,9800,9981,9999,10000,10443,12345,12443,16080,18091,18092,20720,28017,49152 -csv -o output/$cdir/web_intelligence.csv >/dev/null
cat output/$cdir/web_intelligence.csv | cut -d ',' -f9 | grep -v 'url' | anew >output/$cdir/site_list.txtls

##GENERATE SUMMARY##
echo -e "\n\n_\nSUMMARY:"
echo -e "Total unique root domains found: $(cat output/$cdir/rootdomain.txtls | tr '[:upper:]' '[:lower:]' | anew | wc -l)"
echo -e "Total unique subdomains found: $(cat output/$cdir/$cdir.master | tr '[:upper:]' '[:lower:]' | anew | wc -l)"
echo -e "Total unique resolved subdomains found: $(cat live.assets | wc -l) "
echo -e "Total unique web applications found: $(cat output/$cdir/site_list.txtls | tr '[:upper:]' '[:lower:]' | anew | wc -l)"
echo -e "_"
echo -e "Root domain: $(cat output/$cdir/rootdomain.txtls | tr '[:upper:]' '[:lower:]' | anew)"
echo -e "DNS master list:"
cat output/$cdir/$cdir.master

##HOUSE KEEEPING STUFF##
mv output/$cdir/*.txtls output/$cdir/raw_output
mv output/$cdir/raw_output/rootdomain.txtls output/$cdir/
rm live.assets
