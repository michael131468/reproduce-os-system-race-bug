#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <pthread.h>
 
void *worker_thread(void *vargp)
{
    for (int i = 0; i < 1024; i++) {
        int ret = system("echo helloworld > /dev/null");
        if (ret != 0) {
            printf("cmd failed! error=%d\n", ret);
            printf("%d successful runs before failure\n", i);
            return NULL;
        }
    }
    return NULL;
}
  
int main()
{
    pthread_t thread_id;
    pthread_create(&thread_id, NULL, worker_thread, NULL);
    sleep(1);
    for (int i = 0; i < 1024; i++) {
        char* env_decl = (char*) malloc(100 * sizeof(char));
        sprintf(env_decl, "%d=%d", i, i);
        putenv(env_decl);
    }
    pthread_join(thread_id, NULL);
    exit(0);
}
