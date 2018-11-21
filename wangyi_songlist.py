from gevent import monkey
import gevent
import requests
from queue import Queue
from lxml import etree
from pymysql import connect
monkey.patch_all()

class wangyi():
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36',
        }
        self.cat_session = requests.session()
        self.cat_first_page_queue = Queue()
        self.scroll_page_queue = Queue()
        self.get_song_list_queue = Queue()
        self.songs_list_queue = Queue()

    def get_cat_first_page_list(self):
        res = self.cat_session.get("https://music.163.com/discover/playlist", headers=self.headers).content.decode()
        html = etree.HTML(res)
        li_list1 = html.xpath("//div[@id='cateListBox']//dd/a/@href")
        print(len(li_list1))
        li_list2 = []
        for li in li_list1:
            li = 'https://music.163.com' + li
            li_list2.append(li)
            # print(li)
            self.cat_first_page_queue.put(li)

    def scroll_page(self):
        while True:
            print("=====================scrolling pages==================" )
            li = self.cat_first_page_queue.get()
            total_page_list = []
            try:
                res = self.cat_session.get(li, headers=self.headers).content.decode()
                # time.sleep(1)
                html = etree.HTML(res)
                total_num = int(html.xpath("//a[contains(text(),'下一页')]/../a[last()-1]/text()")[0])
                print("此页总数为%s"%total_num)
                for i in range(0, total_num):
                    next = li + '&offset={}'.format(i * 35)
                    total_page_list.append(next)
                    self.scroll_page_queue.put(next)
                # print(total_page_list)
                self.cat_first_page_queue.task_done()
            except :
                print("=================failed to scroll page=================")
                pass

    def get_song_list(self):
        while True:
            print("=================getting song list=================")
            page = self.scroll_page_queue.get()
            total = []
            try:
                res = self.cat_session.get(page, headers=self.headers).content.decode()
                html = etree.HTML(res)
                # print(res)
                lis = html.xpath("//ul[@class = 'm-cvrlst f-cb']/li")
                # print(a)
                for each in lis:
                    item = {}
                    item["name"] = each.xpath("./div[@class='u-cover u-cover-1']/a/@title")[0]
                    item["likes"] = each.xpath(".//div[@class = 'bottom']/span[2]/text()")[0]
                    item["href"] = "https://music.163.com" + each.xpath("./div[@class='u-cover u-cover-1']/a/@href")[0]
                    total.append(item)
                # print(total)
                self.get_song_list_queue.put(total)
                # time.sleep(1)
                print("get song list==============================>successfully")
                self.scroll_page_queue.task_done()
            except:
                print("=================failed to get song list %s===================="%lis)

    def write_and_get_songs(self):
        while True:
            print("=======================writing========================")
            conn = connect(host='localhost', port=3306, user='root', password='123', database='wangyi', charset='utf8')
            cur = conn.cursor()
            songs_item = self.get_song_list_queue.get()
            for item in songs_item:
                try:
                    # sql1 = """insert into yunyinyue (na) values("%s")"""%(item["name"])
                    sql = """insert into yunyinyue (name,likes,href) values("%s","%s","%s");""" %(item["name"], item["likes"], item["href"])
                    cur.execute(sql)
                    conn.commit()
                    # print(item)
                    res = self.cat_session.get(item["href"],headers=self.headers).content.decode()
                    html = etree.HTML(res)
                    # print(html)
                    song_li = html.xpath("//div[@id = 'song-list-pre-cache']/ul/li")
                    songs = []
                    for li in song_li:
                        songs.append("https://music.163.com/#"+"".join(li.xpath("./a/@href")))
                    # print(songs)
                    self.songs_list_queue.put(songs)
                except:
                    pass
                continue
            cur.close()
            conn.close()
            self.get_song_list_queue.task_done()
    def song_list(self):
        while True:
            self.songs = self.songs_list_queue.get()
            yield self.songs
            self.songs_list_queue.task_done()

    def run(self):
        all_event = []
        all_event.append(gevent.spawn(self.get_cat_first_page_list))
        for i in range(2):
            all_event.append(gevent.spawn(self.scroll_page))
            all_event.append(gevent.spawn(self.get_song_list))
        for j in range(3):
            all_event.append(gevent.spawn(self.song_list))
            all_event.append(gevent.spawn(self.write_and_get_songs))
        gevent.joinall(all_event)

def main():
    get_songs = wangyi()
    get_songs.run()

if __name__ == "__main__":
    main()