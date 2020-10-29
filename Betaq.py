# to run: python betdaq_sample_api.py [username]

from xml.dom.minidom import Document, parseString

import http.client, urllib.parse

SOAPNamespaces=[("xmlns:soap", "http://schemas.xmlsoap.org/soap/envelope/"),
                ("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance"),
                ("xmlns:xsd", "http://www.w3.org/2001/XMLSchema")]

Namespace="http://www.GlobalBettingExchange.com/ExternalAPI/"

Endpoints={"read_only": "http://api.betdaq.com/v2.0/ReadOnlyService.asmx",
           "secure": "http://api.betdaq.com/v2.0/Secure/SecureService.asmx"}

UserAgent="python-2.5"

class ApiException(Exception):

    def __init__(self, message):
        Exception.__init__(self, message)

# xml helpers

def add_text_element(doc, parent, name, value):
    element=doc.createElement(name)
    element.appendChild(doc.createTextNode(str(value)))
    parent.appendChild(element)

class BetdaqApi:

    def create_request(self, action, username, annotator=None, password=None):
        doc=Document()
        soapenv=doc.createElement("soap:Envelope")
        for name, value in SOAPNamespaces:
            soapenv.setAttribute(name, value)
        # header
        soapheader=doc.createElement("soap:Header")
        header=doc.createElement("ExternalApiHeader")
        for name, value in [("version", "2"),
                            ("languageCode", "en"),
                            ("username", username),
                            ("xmlns", Namespace)]:
            header.setAttribute(name, value)
        if not password==None:
            header.setAttribute("password", password)
        soapheader.appendChild(header)
        soapenv.appendChild(soapheader)
        # body
        soapbody=doc.createElement("soap:Body")
        action_=doc.createElement(action)
        action_.setAttribute("xmlns", Namespace)
        request=doc.createElement("%sRequest" % (action[0].lower()+action[1:]))
        if not annotator==None:
            annotator(doc, request)
        action_.appendChild(request)
        soapbody.appendChild(action_)
        soapenv.appendChild(soapbody)
        doc.appendChild(soapenv)
        return doc

    def http_post(self, url, action, request):
        urlsegs=urllib.parse.urlparse(url)
        host, port, path = urlsegs[1], 443, urlsegs[2]
        httpp=http.client.HTTPSConnection(host, port)
        payload=request.toxml(encoding="utf-8")
        headers={"SOAPAction": "%s%s" % (Namespace, action),
                 "Content-Type": "text/xml",
                 "User-Agent": UserAgent}
        httpp.request("POST", path, payload, headers)
        resp=httpp.getresponse()
        if not resp.status==200:
            raise ApiException("Betdaq returned HTTP %i" % resp.status)
        doc=parseString(resp.read())
        result=doc.getElementsByTagName("%sResult" % action)[0]
        returnstatus=result.getElementsByTagName("ReturnStatus")[0]
        returncode=int(returnstatus.getAttribute("Code"))
        returndesc=returnstatus.getAttribute("Description")
        if not (returncode==0 and returndesc=="Success"):
            raise ApiException("Betdaq returned ReturnStatus code/description %i/'%s'" % (returncode, returndesc))
        return result

    # api methods

    def get_root_events(self, username):
        endpoint, action = Endpoints["read_only"], "ListTopLevelEvents"
        request=self.create_request(action, username)
        result=self.http_post(endpoint, action, request)
        def parse_element(el):
            name=el.getAttribute("Name")
            id=int(el.getAttribute("Id"))
            return (name, id)
        return [parse_element(el) for el in result.getElementsByTagName("EventClassifiers")]

    def get_events(self, id, username):
        endpoint, action = Endpoints["read_only"], "GetEventSubTreeNoSelections"
        def annotator(doc, request):
            request.setAttribute("WantDirectDescendentsOnly", "true")
            add_text_element(doc, request, "EventClassifierIds", id)
        request=self.create_request(action, username, annotator)
        result=self.http_post(endpoint, action, request)
        def parse_element(el):
            name=el.getAttribute("Name")
            id=int(el.getAttribute("Id"))
            return (name, id)
        events=[parse_element(el) for el in result.getElementsByTagName("EventClassifiers")]
        markets=[parse_element(el) for el in result.getElementsByTagName("Markets")]
        return (events[1:], markets) # ignore root event

# test

if __name__=="__main__":
    try:
        import sys
        if len(sys.argv) < 2:
            raise ApiException("Please enter username")
        api, username = BetdaqApi(), sys.argv[1]
        rootevents=api.get_root_events(username)
        print(rootevents)
        rootevents=dict(rootevents)
        if "Soccer" not in rootevents:
            raise ApiException("Couldn't find Soccer id")
        events, markets = api.get_events(rootevents["Soccer"], username)
        print((events, markets))
    except ApiException as error:
        print(str(error))