import sys
sys.path.append('../')
import smtplib
from email.mime.text import MIMEText
import config

def sendSmtpMail(from_name, from_mail, to_list, sub, content):
    
    mail_user = from_mail['mail_user']
    mail_host = from_mail['mail_host']
    mail_pass = from_mail['mail_pass']
    mail_postfix = from_mail['mail_postfix']
    
    if type(content) == unicode:
        content = content.encode('utf-8')
        
    me = from_name + '<'+mail_user+'@'+mail_postfix+'>'
    msg = MIMEText(content, _charset='utf-8')
    msg['Subject'] = sub
    msg['From'] = me
    msg['To'] = ';'.join(to_list)
    
    try:
        s = smtplib.SMTP()
        s.connect(mail_host)
        s.login(mail_user,mail_pass)
        s.sendmail(me, to_list, msg.as_string())
        s.close()
        return True
    except Exception, e:
        print e
        return False

def mail(title, content):

    from_mail = config.from_mail
    tolist = config.mailto_list
    sendSmtpMail('feedback', from_mail, tolist, title, content)

if __name__ == '__main__':

    from_mail = config.from_mail
    sendSmtpMail('xxx', from_mail, config.mailto_list, sys.argv[1], sys.argv[2])

